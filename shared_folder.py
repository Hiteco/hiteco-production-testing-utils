"""Utility for accessing SMB/CIFS shared folders with credentials."""

import argparse
import getpass
import os
import sys
import smbclient
import smbclient.path
from typing import Optional

try:
    import keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    _KEYRING_AVAILABLE = False

_KEYRING_SERVICE = "shared_folder_smb"


class SharedFolder:
    """
    Manages a connection to an SMB/CIFS shared folder.

    Args:
        share_path: UNC path to the share, e.g. r'\\\\server\\share'
        username:   Domain user, e.g. 'DOMAIN\\user' or just 'user'
        password:   Password for the user
        port:       SMB port (default 445)
    """

    def __init__(self, share_path: str, username: str, password: str, port: int = 445):
        self.share_path = share_path.rstrip("\\").rstrip("/")
        # Extract server name from UNC path (\\server\share)
        parts = self.share_path.lstrip("\\").lstrip("/").split("\\")
        if not parts:
            parts = self.share_path.lstrip("\\").lstrip("/").split("/")
        self.server = parts[0]
        self.username = username
        self.password = password
        self.port = port
        self._connected = False

    def connect(self) -> None:
        """Register the SMB session with the server."""
        smbclient.register_session(
            self.server,
            username=self.username,
            password=self.password,
            port=self.port,
        )
        self._connected = True

    def disconnect(self) -> None:
        """Close the SMB session."""
        smbclient.reset_connection_cache()
        self._connected = False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.disconnect()

    def _full_path(self, *parts: str) -> str:
        """Build a full UNC path relative to the share root."""
        segments = [self.share_path] + [p.strip("\\/") for p in parts if p]
        return "\\".join(segments)

    # ------------------------------------------------------------------
    # Directory listing
    # ------------------------------------------------------------------

    def ls(self, subfolder: str = "") -> list[str]:
        """
        List entries in the share root or a subfolder.

        Returns a list of entry names (files and directories).
        """
        path = self._full_path(subfolder)
        return smbclient.listdir(path)

    # ------------------------------------------------------------------
    # Directory creation
    # ------------------------------------------------------------------

    def mkdir(self, subfolder: str, parents: bool = False) -> None:
        """
        Create a subfolder inside the share.

        Args:
            subfolder: Relative path of the new folder, e.g. 'reports/2025'
            parents:   If True, create intermediate directories as needed
        """
        path = self._full_path(subfolder)
        if parents:
            smbclient.makedirs(path, exist_ok=True)
        else:
            smbclient.mkdir(path)

    # ------------------------------------------------------------------
    # File writing
    # ------------------------------------------------------------------

    def write_file(
        self,
        subfolder: str,
        filename: str,
        content: str | bytes,
        encoding: Optional[str] = "utf-8",
    ) -> None:
        """
        Create or overwrite a file inside a subfolder.

        Args:
            subfolder: Relative path of the target folder
            filename:  Name of the file to create
            content:   Text (str) or binary (bytes) content to write
            encoding:  Text encoding; ignored when content is bytes
        """
        path = self._full_path(subfolder, filename)
        if isinstance(content, bytes):
            with smbclient.open_file(path, mode="wb") as f:
                f.write(content)
        else:
            with smbclient.open_file(path, mode="w", encoding=encoding) as f:
                f.write(content)

    # ------------------------------------------------------------------
    # File reading
    # ------------------------------------------------------------------

    def read_file(
        self,
        subfolder: str,
        filename: str,
        binary: bool = False,
        encoding: str = "utf-8",
    ) -> str | bytes:
        """
        Read a file from a subfolder.

        Args:
            subfolder: Relative path of the folder containing the file
            filename:  Name of the file to read
            binary:    If True, return raw bytes; otherwise return str
            encoding:  Text encoding; ignored when binary=True

        Returns:
            File contents as str or bytes.
        """
        path = self._full_path(subfolder, filename)
        if binary:
            with smbclient.open_file(path, mode="rb") as f:
                return f.read()
        else:
            with smbclient.open_file(path, mode="r", encoding=encoding) as f:
                return f.read()

    def exists(self, subfolder: str = "", filename: str = "") -> bool:
        """Return True if the given path exists on the share."""
        path = self._full_path(subfolder, filename)
        return smbclient.path.exists(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SMB shared folder utility")
    parser.add_argument("--share", required=True, help=r"UNC share path, e.g. \\server\share")
    parser.add_argument("--user", default=None, help="Username — or set SMB_USER env var")
    parser.add_argument("--password", default=None, help="Password — or set SMB_PASSWORD env var (omit to be prompted)")
    parser.add_argument("--port", type=int, default=445, help="SMB port (default 445)")

    sub = parser.add_subparsers(dest="op", required=True)

    # ls
    p_ls = sub.add_parser("ls", help="List files in the share or a subfolder")
    p_ls.add_argument("subfolder", nargs="?", default="", help="Remote subfolder to list")

    # write
    p_write = sub.add_parser("write", help="Upload a local file to a remote subfolder")
    p_write.add_argument("local_file", help="Path of the local file to upload")
    p_write.add_argument("remote_subfolder", help="Destination subfolder on the share")

    # read
    p_read = sub.add_parser("read", help="Download a remote file and save it locally")
    p_read.add_argument("remote_subfolder", help="Subfolder on the share containing the file")
    p_read.add_argument("filename", help="Name of the remote file to read")
    p_read.add_argument(
        "local_dest",
        nargs="?",
        default="",
        help="Local destination path (default: current directory, same filename)",
    )

    # store-creds  (requires keyring)
    sub.add_parser("store-creds", help="Save credentials to Windows Credential Manager (requires --user)")

    args = parser.parse_args()

    # store-creds handled before connecting
    if args.op == "store-creds":
        if not _KEYRING_AVAILABLE:
            print("Error: install keyring first:  pip install keyring", file=sys.stderr)
            sys.exit(1)
        if not args.user:
            print("Error: --user required for store-creds", file=sys.stderr)
            sys.exit(1)
        pwd = getpass.getpass(f"Password for '{args.user}': ")
        keyring.set_password(_KEYRING_SERVICE, args.user, pwd)
        print(f"Credentials for '{args.user}' saved to Windows Credential Manager.")
        sys.exit(0)

    # Resolve credentials: CLI arg > keyring > env var > interactive prompt
    username = args.user or os.environ.get("SMB_USER") or input("Username: ")
    password = args.password
    if not password and _KEYRING_AVAILABLE:
        password = keyring.get_password(_KEYRING_SERVICE, username)
    if not password:
        password = os.environ.get("SMB_PASSWORD") or getpass.getpass("Password: ")

    try:
        with SharedFolder(args.share, username, password, args.port) as sf:

            if args.op == "ls":
                entries = sf.ls(args.subfolder)
                location = args.subfolder or "(root)"
                print(f"Contents of {location}:")
                for entry in entries:
                    print(f"  {entry}")
                print(f"\n{len(entries)} item(s) found.")

            elif args.op == "write":
                local_path = args.local_file
                if not os.path.isfile(local_path):
                    print(f"Error: local file not found: {local_path}", file=sys.stderr)
                    sys.exit(1)
                filename = os.path.basename(local_path)
                if args.remote_subfolder and not sf.exists(args.remote_subfolder):
                    sf.mkdir(args.remote_subfolder, parents=True)
                    print(f"Created remote folder: {args.remote_subfolder}")
                with open(local_path, "rb") as f:
                    content = f.read()
                sf.write_file(args.remote_subfolder, filename, content)
                print(f"Uploaded '{local_path}' -> {args.remote_subfolder}\\{filename}")

            elif args.op == "read":
                content = sf.read_file(args.remote_subfolder, args.filename, binary=True)
                local_dest = args.local_dest or args.filename
                # If local_dest is a directory, append the filename
                if os.path.isdir(local_dest):
                    local_dest = os.path.join(local_dest, args.filename)
                with open(local_dest, "wb") as f:
                    f.write(content)
                print(f"Downloaded '{args.remote_subfolder}\\{args.filename}' -> {local_dest}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
