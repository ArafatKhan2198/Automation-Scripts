"""
Automated File Download Script

This script automates the process of downloading files and directories from a secure remote server using SSH and SFTP.
It connects to a specified remote server, navigates through directories, and allows the user to download individual
files or entire directories. Excluded file patterns are defined to skip specific files during downloads.

Author: Arafat
Date: August 18, 2023

Requirements:
- Python 3.x
- paramiko library (for SSH and SFTP connections)

Instructions:
1. Fill in the server details, including hostname, port, and your username/password.
2. Run the script and follow the prompts to provide case number and local directory for downloads.
3. Choose whether to download entire folders or specific files.
4. Downloads are saved to the specified local directory.

Note: This script handles KeyboardInterrupts gracefully, ensuring proper closure of resources.

"""


import paramiko
import os

def download_directory(sftp, remote_dir, local_dir):
    for item in sftp.listdir_attr(remote_dir):
        if not should_exclude(item.filename):
            remote_path = os.path.join(remote_dir, item.filename)
            local_path = os.path.join(local_dir, item.filename)

            if item.st_mode & 0o4000:  # Download complete Directory
                os.makedirs(local_path, exist_ok=True)
                download_directory(sftp, remote_path, local_path)
            else:  # Download a single File
                remote_size = item.st_size
                print(f"\nDownloading {item.filename} ({format_size(remote_size)})...")
                with open(local_path, 'wb') as local_file:
                    sftp.getfo(remote_path, local_file, callback=lambda x, y: print_progress(x, y, remote_size))
                print(f"\nDownload of {item.filename} complete")

def should_exclude(filename):
    exclude_patterns = ['.sfdcprefix', '.sfdc-file-listing-v1']
    return filename in exclude_patterns

def print_progress(transferred, total, remotefile_size):
    percent = transferred / remotefile_size * 100
    print(f"Progress: {percent:.2f}% - {format_size(transferred)} / {format_size(remotefile_size)}", end='\r')

def format_size(size):
    power = 2**10
    n = 0
    power_labels = {0: '', 1: 'KB', 2: 'MB', 3: 'GB'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.2f} {power_labels[n]}"

try:
    # Server details
    hostname = 'casefiles.sjc.cloudera.com'
    port = 22
    username = input("Enter your user name: ") # Enter your username here
    password = input("Enter your password: ")  # Enter your password here

    # Create an SSH client instance
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Establish SSH connection
    while True:
        try:
            ssh_client.connect(hostname, port=port, username=username, password=password)
            print("SSH connection established.")
        except paramiko.ssh_exception.AuthenticationException:
            print("\nAuthentication failed. Please check your username and password.")
            break
        except paramiko.ssh_exception.SSHException:
            print("\nFailed to establish SSH connection. Please check the server details.")
            break
        except KeyboardInterrupt:
            print("\nDownload process aborted.")
            break

        try:
            # User input
            case_number = input("\nEnter the case number: ")
            local_parent_directory = input("Enter the local parent directory where you want to save the case folder: ")

            # Open an SFTP session
            with ssh_client.open_sftp() as sftp:
                remote_directory = f'/case/{case_number}'

                try:
                    sftp.listdir(remote_directory)
                except IOError:
                    print(f"\nRemote directory '/case/{case_number}' does not exist.")
                    continue

                local_parent_directory = os.path.expanduser(local_parent_directory)
                local_case_directory = os.path.join(local_parent_directory, case_number)

                if not os.path.exists(local_case_directory):
                    os.makedirs(local_case_directory)

                remote_contents = sftp.listdir(remote_directory)
                print(f"\nContents of case file directory {case_number}:")
                print("\n*********************************************************\n")
                for item in remote_contents:
                    print(" " + item)
                print("\n*********************************************************\n")
                choice = input("\nDo you want to download the entire folder? (yes/no): ").lower()

                if choice == 'yes':
                    download_directory(sftp, remote_directory, local_case_directory)
                elif choice == 'no':
                    while True:
                        filename = input("\nEnter the filename you want to download: ")
                        remote_file_path = os.path.join(remote_directory, filename)
                        local_file_path = os.path.join(local_case_directory, filename)

                        try:
                            sftp.stat(remote_file_path)
                            break
                        except FileNotFoundError:
                            print(f"Remote file '{filename}' does not exist. Please enter a valid filename.")

                    with open(local_file_path, 'wb') as local_file:
                        remote_size = sftp.stat(remote_file_path).st_size
                        sftp.getfo(remote_file_path, local_file, callback=lambda x, y: print_progress(x, y, remote_size))
                    print(f"\nDownload of {filename} complete")
                else:
                    print("Invalid choice. Please enter 'yes' or 'no'.")

                print("\nDownload process completed.")

        except KeyboardInterrupt:
            print("\nDownload process aborted.")
            break

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Close the SSH connection
    ssh_client.close()
    print("\nSession has ended.")  # Display session end message
