import os
from pathlib import Path
import paramiko
from typing import Optional, List, Tuple
import logging
import yaml

class ImageManager:
    """Manage image files for Proxmox VE"""
    
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'ImageManager':
        """
        Create ImageManager instance from YAML configuration file
        
        Args:
            yaml_path: Path to YAML configuration file
            
        Returns:
            ImageManager instance
        """
        try:
            with open(yaml_path, 'r') as f:
                config = yaml.safe_load(f)
            
            ssh_config = config.get('sshcfg', {})
            return cls(
                host=ssh_config.get('host'),
                user=ssh_config.get('user'),
                password=ssh_config.get('password'),
                local_path=ssh_config.get('local_image'),
                remote_path=ssh_config.get('remote_image')
            )
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {yaml_path}: {str(e)}")
    
    def __init__(self, host: str, user: str, password: str, 
                 local_path: str = "./images",
                 remote_path: str = "/var/lib/vz/images/install",
                 port: int = 22):
        """
        Initialize Image Manager
        
        Args:
            host: PVE host IP or domain
            user: SSH username
            password: SSH password
            local_path: Local path for images
            remote_path: Remote path for images
            port: SSH port (default: 22)
        """
        if not all([host, user, password]):
            raise ValueError("Host, user, and password are required")
            
        self.host = host
        self.user = user
        self.password = password
        self.port = port
        self.local_path = Path(local_path)
        self.remote_path = remote_path
        
        # Create local directory if it doesn't exist
        self.local_path.mkdir(parents=True, exist_ok=True)
        
        self.ssh = None
        self.sftp = None
        self.logger = logging.getLogger('ProxmoxManager')

    def connect(self) -> bool:
        """Establish SSH connection to PVE host"""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh.connect(
                hostname=self.host,
                username=self.user,
                password=self.password,
                port=self.port
            )
            self.sftp = self.ssh.open_sftp()
            self.logger.info(f"Successfully connected to {self.host}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.host}: {str(e)}")
            return False

    def disconnect(self):
        """Close SSH connection"""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        self.logger.info("Disconnected from PVE host")

    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()

    def list_local_images(self) -> List[str]:
        """List image files in local directory"""
        try:
            # 添加 .iso 到支持的文件格式中
            image_files = [f.name for f in self.local_path.glob("*") 
                        if f.suffix.lower() in ('.img', '.qcow2', '.raw', '.iso')]
            self.logger.info(f"Found {len(image_files)} local image files")
            return image_files
        except Exception as e:
            self.logger.error(f"Failed to list local images: {str(e)}")
            return []


    def list_remote_images(self) -> List[str]:
        """List image files in remote directory"""
        try:
            if not self.sftp:
                raise ConnectionError("Not connected to PVE host")
            
            files = self.sftp.listdir(self.remote_path)
            # 添加 .iso 到支持的文件格式中
            image_files = [f for f in files if f.lower().endswith(('.img', '.qcow2', '.raw', '.iso'))]
            self.logger.info(f"Found {len(image_files)} remote image files")
            return image_files
        except Exception as e:
            self.logger.error(f"Failed to list remote images: {str(e)}")
            return []


    def upload_image(self, filename: str, callback=None) -> bool:
        """
        Upload image file to PVE host
        
        Args:
            filename: Name of the image file in local directory
            callback: Optional callback function for progress updates
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not self.sftp:
                raise ConnectionError("Not connected to PVE host")

            local_file = self.local_path / filename
            if not local_file.exists():
                raise FileNotFoundError(f"Local file not found: {local_file}")

            remote_file = os.path.join(self.remote_path, filename)
            
            # Check if file already exists
            try:
                self.sftp.stat(remote_file)
                self.logger.warning(f"File {filename} already exists on remote")
                return False
            except FileNotFoundError:
                pass

            # Define progress callback if needed
            if callback:
                def progress_callback(transferred: int, total: int):
                    percentage = (transferred / total) * 100
                    callback(percentage)

                self.sftp.put(str(local_file), remote_file, callback=progress_callback)
            else:
                self.sftp.put(str(local_file), remote_file)

            self.logger.info(f"Successfully uploaded {filename}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to upload image: {str(e)}")
            return False

    def delete_image(self, filename: str, local: bool = False) -> bool:
        """
        Delete image file from PVE host or local directory
        
        Args:
            filename: Name of the image file to delete
            local: If True, delete from local directory instead of remote
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if local:
                local_file = self.local_path / filename
                local_file.unlink()
                self.logger.info(f"Successfully deleted local file {filename}")
                return True
            else:
                if not self.sftp:
                    raise ConnectionError("Not connected to PVE host")
                remote_file = os.path.join(self.remote_path, filename)
                self.sftp.remove(remote_file)
                self.logger.info(f"Successfully deleted remote file {filename}")
                return True
        except Exception as e:
            self.logger.error(f"Failed to delete image {filename}: {str(e)}")
            return False

    def verify_image(self, filename: str, local: bool = False) -> Tuple[bool, Optional[int]]:
        """
        Verify if image exists and get its size
        
        Args:
            filename: Name of the image file
            local: If True, verify local file instead of remote
            
        Returns:
            Tuple[bool, Optional[int]]: (exists, file_size)
        """
        try:
            if local:
                local_file = self.local_path / filename
                if local_file.exists():
                    return True, local_file.stat().st_size
                return False, None
            else:
                if not self.sftp:
                    raise ConnectionError("Not connected to PVE host")
                remote_file = os.path.join(self.remote_path, filename)
                file_attr = self.sftp.stat(remote_file)
                return True, file_attr.st_size
        except FileNotFoundError:
            self.logger.warning(f"Image {filename} not found")
            return False, None
        except Exception as e:
            self.logger.error(f"Failed to verify image {filename}: {str(e)}")
            return False, None
