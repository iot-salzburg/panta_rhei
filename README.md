# Panta Rhei
### A scalable and highly performancant streaming platform with inherent semantic data mapping.


## Usage

### GOST

The gost server uses shared data on the samba share. This
volume must be in the Docker directory due to reasons discussed
in this [thread](https://github.com/moby/moby/issues/2745)

Hence, to get started, do this steps on each node first: (including backup)

```bash
sudo cp /etc/fstab /etc/fstab.save
sudo sh -c 'echo "" >> /etc/fstab'
sudo sh -c 'echo "# Adding this line for docker swarm sensorthings" >> /etc/fstab'
sudo sh -c 'echo "//192.168.48.60/samba-share/il08X/PantaRhei/gost-db /srv/panta-rhei/gost_server/samba-mount cifs auto,password=,uid=1000,gid=0 0 0" >> /etc/fstab'
sudo mkdir -p /srv/panta-rhei/gost_server/samba-mount
sudo mount -a
```


schreib a systemd service. des wird im gost-db eine kopiert und synchronisiert
zwischen ./samba-data und/var/lib/postgres/data
