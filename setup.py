from bot_manager import * 
from sql import SQLManager
import subprocess
import sys

def define_database():
    manager = SQLManager()
    manager.reset_to_default(config=CONFIG_FILENAME)

def install_modules():
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', '--version'])
    except subprocess.CalledProcessError:
        print("Error: pip is not currently installed or was unable to be located by setup.py.")
        return
    
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("Requirements installed!")
    except subprocess.CalledProcessError:
        print("Error installing one or more required packages.")

    # Install discord.py from the repo

    try:
        subprocess.check_call([sys.executable, 'discord.py/setup.py'])
    except subprocess.CalledProcessError:
        print("Error installing discord.py from provided files. Maybe try cloning the repo?")


if __name__ == "__main__":
    install_modules()
    inp = input("WARNING!!!! RUNNING define_database() WILL RESET ANY CURRENTLY EXISTING DATABASE\nDO NOT RUN IF YOU WISH TO RETAIN THE DATA WITHIN!!!\nDo you wish to proceed anyway? (Y/N)")
    if inp.lower() == "y":
        define_database()
    else:
        print("Skipping database defining!")