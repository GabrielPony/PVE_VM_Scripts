import sys
from utils.logger import Logger
from modules.pve_tools import ProxmoxVMManager
from pathlib import Path
from modules.image_manager import ImageManager

logger = Logger.get_logger()
def push_image(config_path: str):
    try:
        manager = ImageManager.from_yaml(config_path)
        
        with manager:
            local_images = manager.list_local_images()
            remote_images = manager.list_remote_images()
            logger.info(f"Local images: {local_images}")
            logger.info(f"Remote images: {remote_images}")
            
            new_images = [img for img in local_images if img not in remote_images]
            
            if not new_images:
                logger.info("No new images to upload")
                return
                
            logger.info(f"Found {len(new_images)} new images to upload")
            
            BAR_WIDTH = 50
            last_percentage = -1
            GREEN = '\033[32m'
            RESET = '\033[0m'
            
            def show_progress(percentage):
                nonlocal last_percentage
                current_percentage = int(percentage)
                if current_percentage != last_percentage:
                    filled = int(BAR_WIDTH * percentage / 100)
                    bar = '#' * filled + '_' * (BAR_WIDTH - filled)
                    print(f"\r{GREEN}Upload progress: [{bar}] {percentage:.1f}%{RESET}", end='', flush=True)
                    if percentage >= 100:
                        print()
                    last_percentage = current_percentage

            for i, image in enumerate(new_images, 1):
                logger.info(f"Uploading image {i}/{len(new_images)}: {image}")
                manager.upload_image(image, callback=show_progress)
                
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
