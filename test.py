import requests

# Server endpoint
url = "http://localhost:8080/invocations"

# Request payload
payload = {"prompt": "What is Amazon Bedrock?"}

try:
    # Send POST request to AgentCore
    response = requests.post(url, json=payload)

    # Extract and print the agent's response
    result = response.json()["result"]

    # Print the agent's response
    print(result)
except Exception as e:
    # Handle any errors that occur
    print(f"Error: {e}")