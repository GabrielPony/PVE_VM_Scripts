#!/usr/bin/env python3

import yaml
import sys
import time
from utils.logger import Logger
from pathlib import Path
from typing import Dict, List, Optional
from proxmoxer import ProxmoxAPI
from pprint import pformat
import requests
from urllib3.exceptions import InsecureRequestWarning

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

class ProxmoxVMManager:
    logger = Logger.get_logger()
    def __init__(self, config_path: str):
        """Initialize Proxmox VM Manager"""
        self.config_path = config_path
        self.config = self._load_config()
        self.proxmox = self._connect_proxmox()
        self.node = self.config['proxmox']['node']

    def _load_config(self) -> dict:
        """Load configuration file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if not self._validate_config(config):
                    raise ValueError("Configuration validation failed")
                return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration file: {e}")
            sys.exit(1)

    def _validate_config(self, config: dict) -> bool:
        """Validate required fields in configuration file"""
        required_sections = ['proxmox', 'storage', 'vms']
        if not all(section in config for section in required_sections):
            self.logger.error("Missing required sections in configuration file")
            return False

        for vm in config['vms']:
            required_vm_fields = ['id', 'name', 'memory', 'cores']
            if not all(field in vm for field in required_vm_fields):
                self.logger.error(f"VM configuration {vm.get('name', 'Unknown')} missing required fields")
                return False
        return True

    def _connect_proxmox(self) -> ProxmoxAPI:
        """Connect to Proxmox server"""
        try:
            proxmox_config = self.config['proxmox']
            return ProxmoxAPI(
                proxmox_config['host'],
                user=proxmox_config['user'],
                password=proxmox_config['password'],
                verify_ssl=proxmox_config['verify_ssl']
            )
        except Exception as e:
            self.logger.error(f"Failed to connect to Proxmox: {e}")
            sys.exit(1)

    def _wait_for_task(self, task_upid: str, timeout: int = 300) -> bool:
        """Wait for task completion"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            task_status = self.proxmox.nodes(self.node).tasks(task_upid).status.get()
            if task_status['status'] == 'stopped':
                if task_status['exitstatus'] == 'OK':
                    return True
                else:
                    self.logger.error(f"Task failed: {task_status}")
                    return False
            time.sleep(1)
        self.logger.error("Task timeout")
        return False

    def _validate_vm_config(self, vm_config: dict) -> bool:
        """Validate VM configuration"""
        # Check if VM ID already exists
        existing_vms = self.proxmox.nodes(self.node).qemu.get()
        if any(vm['vmid'] == vm_config['id'] for vm in existing_vms):
            self.logger.error(f"VM ID {vm_config['id']} already exists")
            return False

        # Validate required parameters
        required_params = ['id', 'name', 'memory', 'cores']
        if not all(param in vm_config for param in required_params):
            missing = [param for param in required_params if param not in vm_config]
            self.logger.error(f"Missing required parameters: {missing}")
            return False

        return True

    def _prepare_create_params(self, vm_config: dict) -> dict:
        """Prepare VM creation parameters"""
        create_params = {
            'vmid': vm_config['id'],
            'name': vm_config['name'],
            'memory': vm_config['memory'],
            'cores': vm_config['cores'],
        }

        # Add optional basic parameters
        optional_params = {
            'sockets', 'ostype', 'scsihw', 'cpu', 'acpi', 'ide2',
            'scsi0', 'net0'
        }
        for param in optional_params:
            if param in vm_config:
                create_params[param] = vm_config[param]

        # Handle boot order
        if 'boot_order' in vm_config:
            boot_order = ','.join(vm_config['boot_order'])
            create_params['boot'] = f"order={boot_order}"

        # Handle cloud-init configuration
        if vm_config.get('cloud_init') and 'ci' in vm_config:
            ci_params = {
                'ciuser': vm_config['ci'].get('user'),
                'cipassword': vm_config['ci'].get('password'),
                'sshkeys': vm_config['ci'].get('ssh_key'),
                'ipconfig0': vm_config['ci'].get('ip_config')
            }
            create_params.update({k: v for k, v in ci_params.items() if v is not None})

        return create_params

    def _apply_post_create_config(self, vm_config: dict) -> bool:
        """Apply post-creation configuration"""
        try:
            vmid = vm_config['id']
            
            # Set tags
            if 'tags' in vm_config:
                self.proxmox.nodes(self.node).qemu(vmid).config.put(
                    tags=vm_config['tags']
                )

            self.logger.info(f"VM {vm_config['name']} (ID: {vmid}) created successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to apply post-creation configuration: {e}")
            return False


    # def wait_for_vm_ready(self, vmid: int, timeout: int = 1800) -> bool:
    #     """Wait for VM installation to complete"""
    #     start_time = time.time()
    #     while time.time() - start_time < timeout:
    #         try:
    #             status = self.proxmox.nodes(self.node).qemu(vmid).status.current.get()
    #             if status['status'] == 'stopped':
    #                 self.logger.info(f"VM {vmid} installation completed")
    #                 return True
    #             time.sleep(10)
    #         except Exception as e:
    #             self.logger.error(f"Error checking VM status: {e}")
    #             return False
    #     self.logger.error(f"Timeout waiting for VM {vmid} installation")
    #     return False

    # def update_boot_order(self, vmid: int, boot_order: List[str]) -> bool:
    #     """Update VM boot order"""
    #     try:
    #         order = ','.join(boot_order)
    #         self.proxmox.nodes(self.node).qemu(vmid).config.put(
    #             boot=f"order={order}"
    #         )
    #         return True
    #     except Exception as e:
    #         self.logger.error(f"Failed to update boot order: {e}")
    #         return False

    def create_vm(self, vm_config: dict) -> bool:
        """Create virtual machine"""
        try:
            # Validate VM configuration
            if not self._validate_vm_config(vm_config):
                return False

            # Prepare creation parameters
            create_params = self._prepare_create_params(vm_config)
            self.logger.info(f"VM creation parameters:\n{pformat(create_params)}")

            # Create VM
            self.logger.info(f"Starting VM creation: {vm_config['name']} (ID: {vm_config['id']})")
            result = self.proxmox.nodes(self.node).qemu.create(**create_params)
            
            if not self._wait_for_task(result):
                return False

            # Apply post-creation configuration
            return self._apply_post_create_config(vm_config)

        except Exception as e:
            self.logger.error(f"Error occurred while creating VM: {e}")
            return False

    def create_all_vms(self) -> tuple[int, int]:
        """Create all configured virtual machines"""
        success = 0
        failed = 0
        total = len(self.config['vms'])

        self.logger.info(f"Starting creation of {total} virtual machines")

        for idx, vm_config in enumerate(self.config['vms'], 1):
            self.logger.info(f"\n[{idx}/{total}] Creating VM: {vm_config['name']} (ID: {vm_config['id']})")
            
            if self.create_vm(vm_config):
                success += 1
            else:
                failed += 1
                self.logger.error(f"VM {vm_config['name']} (ID: {vm_config['id']}) creation failed")

        self.logger.info(f"\nCreation completed: {success} successful, {failed} failed")
        return success, failed
