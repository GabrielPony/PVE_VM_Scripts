import sys
from utils.logger import Logger
from modules.pve_tools import ProxmoxVMManager
from pathlib import Path


def main():
    # Get script directory
    logger = Logger.get_logger()
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

    # Confirm whether to continue
    if input("\nProceed with VM creation? (y/N): ").lower() != 'y':
        logger.info("Operation cancelled")
        sys.exit(0)

    # Create virtual machines
    success, failed = vm_manager.create_all_vms()

    # Exit code
    sys.exit(1 if failed > 0 else 0)

if __name__ == "__main__":
    main()
