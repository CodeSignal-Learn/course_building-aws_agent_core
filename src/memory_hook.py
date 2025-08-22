from bedrock_agentcore.memory import MemoryClient
from strands.hooks import AgentInitializedEvent, HookProvider, HookRegistry, MessageAddedEvent

class MemoryHookProvider(HookProvider):
    def __init__(self, memory_client: MemoryClient, memory_id: str, actor_id: str, session_id: str):
        self.memory_client = memory_client
        self.memory_id = memory_id
        self.actor_id = actor_id
        self.session_id = session_id

    def on_agent_initialized(self, event: AgentInitializedEvent):
        """Load recent conversation history when agent starts"""
        try:
            # Load the last 10 conversation turns from memory
            recent_turns = self.memory_client.get_last_k_turns(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                k=10
            )

            if recent_turns:
                # Format conversation history for the agent's expected format
                formatted_messages = []
                for turn in recent_turns:
                    for message in turn:
                        role = message['role'].lower()  # Convert to lowercase (user/assistant)
                        content_text = message['content']['text']

                        formatted_message = {
                            "role": role,
                            "content": [
                                {
                                    "text": content_text
                                }
                            ]
                        }
                        formatted_messages.append(formatted_message)

                # Set the formatted messages to the agent
                event.agent.messages = formatted_messages

        except Exception as e:
            print(f"Memory load error: {e}")

    def on_message_added(self, event: MessageAddedEvent):
        """Store messages in memory"""
        messages = event.agent.messages
        try:
            # Get the last message
            last_message = messages[-1]

            # Extract text content and role from last message
            content_text = last_message["content"][0].get("text", "")
            role = last_message["role"]

            # Create a new event with the last message
            self.memory_client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                messages=[(content_text, role)]
            )
        except Exception as e:
            print(f"Memory save error: {e}")

    def register_hooks(self, registry: HookRegistry):
        # Register memory hooks
        registry.add_callback(MessageAddedEvent, self.on_message_added)
        registry.add_callback(AgentInitializedEvent, self.on_agent_initialized)