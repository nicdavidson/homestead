"""
Hearth Integrations - CLI
Command-line interface for direct interaction.
"""

import sys
import time
import threading
from typing import Optional

from core import Config, get_config
from agents import Gateway


class ThinkingIndicator:
    """Shows a thinking indicator while processing."""

    def __init__(self, message="Thinking"):
        self.message = message
        self.running = False
        self.thread = None

    def _animate(self):
        """Animate the thinking indicator."""
        dots = 0
        while self.running:
            sys.stdout.write(f"\r{self.message}{'.' * (dots % 4)}   ")
            sys.stdout.flush()
            time.sleep(0.3)
            dots += 1

    def __enter__(self):
        self.running = True
        self.thread = threading.Thread(target=self._animate)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write("\r" + " " * 50 + "\r")  # Clear line
        sys.stdout.flush()


class CLI:
    """
    Command-line interface for Hearth.
    
    Provides:
    - Interactive chat
    - One-shot commands
    - REPL mode
    """
    
    def __init__(self, config: Optional[Config] = None, agent: str = "main"):
        self.config = config or get_config()
        self.gateway = Gateway(config)
        self._session_id = "cli-interactive"
        self.agent = agent  # 'main', 'sonnet', 'grok', or 'auto' for routing

        # Resolve 'main' to configured main agent (default: sonnet)
        if self.agent == "main":
            self.agent = self.config.get("chat.main_agent", "sonnet")
    
    def chat(self, message: Optional[str] = None):
        """
        Interactive chat mode or single message.
        
        If message is provided, process and return.
        Otherwise, enter REPL mode.
        """
        if message:
            return self._process(message)
        
        self._repl()
    
    def _process(self, message: str) -> str:
        """Process a single message and return response."""
        if self.agent == "auto":
            # Use router
            response = self.gateway.process(
                message,
                channel="cli",
                session_id=self._session_id
            )
            return response.content
        else:
            # Direct to specific agent
            history = self.gateway._get_history(self._session_id)

            if self.agent == "sonnet":
                agent_response = self.gateway.sonnet.converse(message, history)
            elif self.agent == "grok":
                agent_response = self.gateway.grok.chat(message, context=history, include_identity=True)
            else:
                # Fallback to sonnet
                agent_response = self.gateway.sonnet.converse(message, history)

            # Update history
            self.gateway._update_history(self._session_id, message, agent_response.content)
            return agent_response.content
    
    def _repl(self):
        """Run interactive REPL."""
        name = self.gateway.identity.get_name()
        
        print(f"\n{'=' * 60}")
        print(f"  Hearth - {name}")
        print(f"{'=' * 60}")
        print("Type 'exit' or 'quit' to leave. 'help' for commands.\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ("exit", "quit", "q"):
                    print("\nGoodbye.")
                    break
                
                if user_input.lower() == "help":
                    self._print_help()
                    continue
                
                if user_input.lower() == "clear":
                    self._session_id = f"cli-{id(self)}"  # New session
                    print("Session cleared.\n")
                    continue
                
                # Process message with thinking indicator
                with ThinkingIndicator(f"{name} is thinking"):
                    if self.agent == "auto":
                        # Use router
                        response = self.gateway.process(
                            user_input,
                            channel="cli",
                            session_id=self._session_id
                        )
                        print(f"\n{name}: {response.content}")
                        if self.config.debug:
                            print(f"  [{response.model} | {response.intent} | ${response.cost:.4f}]")
                    else:
                        # Direct to specific agent
                        history = self.gateway._get_history(self._session_id)

                        if self.agent == "sonnet":
                            agent_response = self.gateway.sonnet.converse(user_input, history)
                        elif self.agent == "grok":
                            agent_response = self.gateway.grok.chat(user_input, context=history, include_identity=True)
                        else:
                            agent_response = self.gateway.sonnet.converse(user_input, history)

                        # Update history
                        self.gateway._update_history(self._session_id, user_input, agent_response.content)

                        print(f"\n{name}: {agent_response.content}")
                        if self.config.debug:
                            print(f"  [{agent_response.model} | direct | ${agent_response.cost:.4f}]")
                
                print()
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'exit' to quit properly.")
            except EOFError:
                print("\nGoodbye.")
                break
            except Exception as e:
                print(f"\nError: {e}\n")
    
    def _print_help(self):
        """Print help message."""
        print("""
Commands:
  status    - Show system status
  costs     - Show cost report
  reflect   - Trigger self-reflection
  newspaper - Generate morning summary
  clear     - Clear conversation history
  exit/quit - Exit the chat
  help      - Show this message

Otherwise, just type to chat!
""")


def run_cli(config: Optional[Config] = None, message: Optional[str] = None, agent: str = "main"):
    """Run CLI (interactive or single message)."""
    cli = CLI(config, agent=agent)

    if message:
        print(cli.chat(message))
    else:
        cli.chat()


# Alias for main.py
run_cli_chat = run_cli
