class Commands:

    @staticmethod
    def is_command(text):

        return text.startswith("/")

    @staticmethod
    def execute(command, chat, brain, voice_state=None, personality=None, voice_engine=None):

        if command == "/help":

            print("""
Commands

/help
/history
/clear
/model
/voice          — show voice status
/voice on       — enable spoken responses
/voice off      — disable spoken responses
/exit
""")

            return True

        elif command == "/history":

            for message in chat.get_history():

                print(f'{message["role"]}: {message["content"]}')

            return True

        elif command == "/clear":

            chat.clear()

            print("Conversation Cleared.")

            return True

        elif command == "/model":

            print(brain.provider)

            return True

        elif command == "/voice on":
            if voice_state is not None:
                voice_state["enabled"] = True
                greeting = personality.get_greeting() if personality else "Voice output enabled."
                print(f"\nEDITH > 🔊 {greeting}")
                if voice_engine:
                    voice_engine.speak(greeting)
            return True

        elif command == "/voice off":
            if voice_state is not None:
                voice_state["enabled"] = False
                print("\nEDITH > 🔇 Voice output disabled.")
                if voice_engine:
                    voice_engine.speak("Voice output disabled.")
            return True

        elif command == "/voice":
            if voice_state is not None:
                status = "ON 🔊" if voice_state["enabled"] else "OFF 🔇"
                print(f"\nEDITH > Voice is currently {status}.")
            return True

        return False