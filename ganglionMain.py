import subprocess
if __name__=="__main__":
    command = ["textual-web", "--config","ganglion.toml"]
    print("REACHED HERE____")
    # process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    # Run the command in the foreground and wait for it to complete
    ans = subprocess.call(command, shell=True)