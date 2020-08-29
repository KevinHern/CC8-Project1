# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

# Imports
import log

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    while True:
        mode = input("What operation mode do you want to run? Client(c)/Server(s)\t")
        if mode == "c":
            # Configure Logger
            logger = log.Logger(0, 'client.app')

            # Start Client
            pass
        elif mode == "s":
            # Configure Logger
            logger = log.Logger(1, 'server.app')
            logger.log_this("Server is ready")

            # Start Server
            pass
        else:
            print("Sorry, I didn't understands. Try again")
            pass

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
