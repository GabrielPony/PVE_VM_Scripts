import sys
from utils.logger import Logger
from modules.pve_tools import ProxmoxVMManager
from pathlib import Path
from modules.image_manager import ImageManager

logger = Logger.get_logger()
def push_image(config_path: str):
    """
    Push images to remote server using configuration from specified path
    
    Args:
        config_path: Path to YAML configuration file
    """
    try:
        # 从YAML文件创建实例
        manager = ImageManager.from_yaml(config_path)
        
        # 使用上下文管理器
        with manager:
            # 列出本地和远程镜像
            local_images = manager.list_local_images()
            remote_images = manager.list_remote_images()
            logger.info(f"Local images: {local_images}")  # 使用 f-string
            logger.info(f"Remote images: {remote_images}")  # 使用 f-string
            
            # 上传镜像
            if local_images:
                def show_progress(percentage):
                    logger.info(f"Upload progress: {percentage:.2f}%")
                    
                manager.upload_image(local_images[0], callback=show_progress)
            else:
                logger.warning("No local images found to upload")
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")


def main():
    # Get script directory
    script_dir = Path(__file__).parent
    config_path = script_dir / "./configs/vm_config.yaml"

    logger.info("Start checking config files")
    # Check if configuration file exists
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)

    # Create VM manager
    vm_manager = ProxmoxVMManager(str(config_path))

    # Display configuration information
    logger.info(f"Configuration file loaded: {config_path}")
    logger.info(f"Number of VMs to create: {len(vm_manager.config['vms'])}")

    logger.info(f"Push image to PVE\n")
    push_image(config_path)

    # # Confirm whether to continue
    # if input("\nProceed with VM creation? (y/N): ").lower() != 'y':
    #     logger.info("Operation cancelled")
    #     sys.exit(0)

    # Create virtual machines
    success, failed = vm_manager.create_all_vms()

    # Exit code
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    main()
