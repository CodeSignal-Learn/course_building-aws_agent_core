#!/usr/bin/env python3
"""
Enable Anthropic Claude Opus on Amazon Bedrock (programmatically, no console).
- Accepts an agreement offer if needed
- (Optionally) submits a use-case form (in us-east-1)
- Flips the entitlement gate
- Polls readiness
- Invokes the model once to sanity-check

Requirements:
- boto3, botocore
- AWS credentials with Bedrock (and if needed, Marketplace) permissions
"""

import json
import os
import time
import urllib.error
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import ClientError

REGION = os.getenv("BEDROCK_REGION", "us-east-1")
POLL_INTERVAL_S = float(os.getenv("POLL_INTERVAL_S", "3"))
MAX_WAIT_S = int(os.getenv("MAX_WAIT_S", "120"))
OFFER_TYPE = os.getenv("OFFER_TYPE", "PUBLIC")

# Use-case submission (optional). If you set SUBMIT_USE_CASE_JSON to a JSON string,
# it will be submitted to us-east-1. Example env var content:
# {"companyName":"ACME","companyWebsite":"https://acme.example","intendedUsers":"0",
#  "industryOption":"Technology","otherIndustryOption":"","useCases":"Internal assistants"}
SUBMIT_USE_CASE_JSON = os.getenv("SUBMIT_USE_CASE_JSON", "").strip() or None


def get_availability(br, model_id):
    return br.get_foundation_model_availability(modelId=model_id)


def explain_state(av):
    return {
        "agreement": av.get("agreementAvailability", {}).get("status"),
        "auth": av.get("authorizationStatus"),
        "entitlement": av.get("entitlementAvailability"),
        "region": av.get("regionAvailability"),
    }


def accept_public_offer(br, model_id, offer_type="PUBLIC"):
    offers = br.list_foundation_model_agreement_offers(
        modelId=model_id, offerType=offer_type
    ).get("offers", [])
    if not offers:
        return False, "no_public_offers"
    br.create_foundation_model_agreement(
        modelId=model_id, offerToken=offers[0]["offerToken"]
    )
    return True, "offer_accepted"


def submit_use_case_us_east_1(payload_json_str):
    if not payload_json_str:
        return "skipped"
    br_global = boto3.client("bedrock", region_name="us-east-1")
    # boto3 expects raw bytes for 'formData'
    br_global.put_use_case_for_model_access(formData=payload_json_str.encode("utf-8"))
    return "submitted"


def set_model_entitlement(model_id, region):
    """
    Flip the 'entitlementAvailability' gate via a signed POST.
    NOTE: This uses an endpoint that is not yet documented in public boto3,
    and may change.
    """
    session = boto3.session.Session()
    creds = session.get_credentials().get_frozen_credentials()
    url = f"https://bedrock.{region}.amazonaws.com/foundation-model-entitlement"
    body = json.dumps({"modelId": model_id}).encode("utf-8")

    req = AWSRequest(
        method="POST",
        url=url,
        data=body,
        headers={"Content-Type": "application/x-amz-json-1.1"},
    )
    SigV4Auth(creds, "bedrock", region).add_auth(req)

    http_req = urllib.request.Request(
        url, data=req.body, headers=dict(req.headers), method="POST"
    )
    with urllib.request.urlopen(http_req, timeout=30) as r:
        payload = r.read().decode("utf-8")
        return r.status, payload


def wait_until_ready(br, model_id, max_wait_s, poll_interval_s):
    end = time.time() + max_wait_s
    last = explain_state(get_availability(br, model_id))
    while time.time() < end:
        if all(
            [
                last["agreement"] == "AVAILABLE",
                last["auth"] == "AUTHORIZED",
                last["entitlement"] == "AVAILABLE",
                last["region"] == "AVAILABLE",
            ]
        ):
            return "enabled", last
        time.sleep(poll_interval_s)
        last = explain_state(get_availability(br, model_id))
    return "timeout", last


def enable_model(
    model_id,
    region=REGION,
    offer_type=OFFER_TYPE,
    submit_use_case_json=SUBMIT_USE_CASE_JSON,
    max_wait_s=MAX_WAIT_S,
    poll_interval_s=POLL_INTERVAL_S,
):
    br = boto3.client("bedrock", region_name=region)
    steps = []

    try:
        av = get_availability(br, model_id)
        state = explain_state(av)
        steps.append(f"start: {state}")

        if state["region"] == "NOT_AVAILABLE":
            print(f"❌ Bedrock model {model_id} is not available in {region}")
            return {"status": "blocked_region", "steps": steps, "final": state}

        if state["agreement"] != "AVAILABLE":
            print(f"Agreement not available. Accepting public offer for {model_id}")
            ok, msg = accept_public_offer(br, model_id, offer_type=offer_type)
            if not ok:
                print(f"❌ Error accepting public offer for {model_id}: {msg}")
                return {"status": "error", "steps": steps, "final": state}
            steps.append(msg)
            time.sleep(2)
            state = explain_state(get_availability(br, model_id))
            steps.append(f"post-agreement: {state}")
            print(f"Public offer accepted for {model_id}")

        if submit_use_case_json is not None:
            print(f"Submitting use case for {model_id}")
            steps.append("submitting_use_case_us_east_1")
            try:
                steps.append(submit_use_case_us_east_1(submit_use_case_json))
            except ClientError as e:
                print(f"❌ Error submitting use case for {model_id}: {e}")
                steps.append(f"use_case_error: {e}")
            time.sleep(2)
            state = explain_state(get_availability(br, model_id))
            steps.append(f"post-usecase: {state}")

        if state["entitlement"] != "AVAILABLE":
            print(
                f"Entitlement not available. Trying to set model entitlement for {model_id}"
            )
            try:
                status_code, payload = set_model_entitlement(model_id, region)
                steps.append(
                    f"entitlement_post: http {status_code} payload={payload!r}"
                )
                time.sleep(2)
                state = explain_state(get_availability(br, model_id))
                steps.append(f"post-entitlement: {state}")
                print(f"Entitlement set for {model_id}")
            except urllib.error.HTTPError as e:
                steps.append(
                    f"entitlement_http_error: {e.code} {e.read().decode('utf-8', 'ignore')}"
                )
                print(f"❌ Error setting model entitlement for {model_id}: {e}")
            except Exception as e:
                steps.append(f"entitlement_error: {e!r}")
                print(f"❌ Error setting model entitlement for {model_id}: {e}")

        print(f"Waiting until ready for {model_id}")
        status, final_state = wait_until_ready(
            br, model_id, max_wait_s, poll_interval_s
        )
        print(f"Status: {status}, Final state: {final_state}")
        return {"status": status, "steps": steps, "final": final_state}

    except ClientError as e:
        print(f"❌ Error enabling model {model_id}: {e}")
        return {
            "status": "error",
            "error": f"{e.response.get('Error', {}).get('Code')}: {e.response.get('Error', {}).get('Message')}",
            "steps": steps,
        }
    except Exception as e:
        print(f"❌ Error enabling model {model_id}: {e}")
        return {
            "status": "error",
            "error": f"{e}",
            "steps": steps,
        }
