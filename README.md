# PVE_VM_Scripts
Use this scripts, you can create pve vm very convenient.

## Host Info
OS: Ubuntu 22.04

## Prepare Host Env 
```bash
sudo apt-get install python3 python3-pip
```

## Prepare Files for Scripts
- images: copy `img` files or `iso` files to images
```bash
mkdir images
cp -r local/test.img ./images
```

- configs: copy `vm_config_temp.yaml` to `vm_config.yaml` 
```bash
cp vm_config_temp.yaml vm_config.yaml
```