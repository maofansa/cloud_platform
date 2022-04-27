<domain type='kvm'>
  <name>MyGuest</name>
  <uuid>5679fd8b-e95b-4269-953f-34c7a8067b90</uuid>
  <title>A short description - title - of the domain</title>
  <description>Some human readable description</description>
  <memory unit='KiB'>1048576</memory>
  <currentMemory unit='KiB'>1048576</currentMemory>
  <vcpu placement='static'>1</vcpu>
  <os>
    <type arch='x86_64' machine='pc-i440fx-rhel7.0.0'>hvm</type>
    <boot dev='hd'/>
    <boot dev='cdrom'/>
  </os>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <pm>
    <suspend-to-mem enabled='no'/>
    <suspend-to-disk enabled='no'/>
  </pm>
  <devices>
    <emulator>/usr/libexec/qemu-kvm</emulator>
    <disk type='network' device='disk'>
      <driver name='qemu'/>
      <auth username='libvirt'>
        <secret type='ceph' uuid='41801fed-be4b-400d-87c8-525d6340fcb0'/>
      </auth>
      <source protocol='rbd' name='libvirt-pool/ceph-test.img'>
        <host name='ceph1' port='6789'/>
        <host name='ceph2' port='6789'/>
      </source>
      <target dev='vda' bus='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x07' function='0x0'/>
    </disk>
    <disk type='file' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source file='/mnt/cephfs/libvirt/iso/CentOS-7-x86_64-DVD-2009.iso'/>
      <target dev='hda' bus='ide'/>
      <readonly/>
      <address type='drive' controller='0' bus='0' target='0' unit='0'/>
    </disk>
    <interface type='network'>
      <source network='default'/>
      <model type='virtio'/>
      <address type='pci' domain='0x0000' bus='0x00' slot='0x03' function='0x0'/>
    </interface>
    <input type='mouse' bus='ps2'/>
    <input type='keyboard' bus='ps2'/>
    <graphics type='spice' autoport='yes'>
      <listen type='address'/>
      <image compression='off'/>
    </graphics>
    <graphics type='vnc' port='-1'/>
  </devices>
</domain>
