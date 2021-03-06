'''
zstack snapshot test class

@author: Youyk
'''
import zstackwoodpecker.header.snapshot as sp_header
import zstackwoodpecker.header.vm as vm_header
import zstackwoodpecker.header.volume as volume_header
import zstackwoodpecker.header.image as image_header
import zstackwoodpecker.operations.volume_operations as vol_ops
import zstackwoodpecker.operations.resource_operations as res_ops
import zstackwoodpecker.operations.image_operations as img_ops
import zstackwoodpecker.test_util as test_util
import zstackwoodpecker.test_lib as test_lib

import uuid

checking_point_folder = '%s/checking_point' % test_lib.WOODPECKER_MOUNT_POINT

def is_ancestry(snapshot1, snapshot2):
    '''
    Return True, if snapshot2 is snapshot1's ancestry
    '''
    parent = snapshot1.get_parent()
    while parent:
        if parent == snapshot2:
            return True
        parent = parent.get_parent()

def get_snapshot_family(snapshot):
    sp_list = [snapshot]
    if not snapshot.get_child_list():
        return sp_list

    for sp in snapshot.get_child_list():
        sp_list.extend(get_snapshot_family(sp))

    return sp_list

def get_all_ancestry(snapshot):
    '''
    Return ancestry chain
    '''
    snapshot_chain = [snapshot]
    parent = snapshot.get_parent()
    if parent:
        snapshot_chain.extend(get_all_ancestry(parent))

    return snapshot_chain

def print_snapshot_chain_checking_point(snapshot_chain):
    checking_point_chain = ['Snapshot Chain Checking Point List:']
    num = 1
    for sp in snapshot_chain:
        name = sp.get_snapshot().name
        uuid = sp.get_snapshot().uuid
        checking_point = sp.get_checking_point()
        checking_point_info = '\t[%s]: [snapshot:]%s [uuid:]%s\
                [checking_point:] %s' % (num, name, uuid, checking_point)
        checking_point_chain.append(checking_point_info)
        num += 1

    print_info = '\n'.join(checking_point_chain)
    test_util.test_logger(print_info)
    return print_info

class ZstackVolumeSnapshot(object):
    '''
    Ideally ZstackVolumeSnapshot should inherit from ZstackTestVolume, since
    all snapshot operations are just belonged to a Volume actions. And it will
    be easy to remove self.utiltiy_vm . But the only issue is, when Volume is 
    deleted, snapshots structure might be still exist, if there is any snapshot
    in backuped stage. So Volume.delete() might be not remove this object. Then
    we can't just inherit ZstackTestVolume class.
    '''
    def __init__(self):
        self.current_snapshot = None
        self.snapshot_head = None #The header of snapshot tree
        self.target_volume = None
        self.utility_vm = None
        self.snapshot_list = []
        self.original_checking_points = []
        self.state = None
        self.primary_snapshots = []
        self.backuped_snapshots = []
        self.volume_type = None #Root volume or data volume

    def __repr__(self):
        if self.target_volume and self.target_volume.get_volume():
            return '%s-for-volume-%s' % (self.__class__.__name__, self.target_volume.get_volume().uuid)
        return '%s-None' % self.__class__.__name__

    def set_volume_type(self, volume_type):
        self.volume_type = volume_type

    def get_volume_type(self):
        return self.volume_type

    def get_checking_points(self, snapshot):
        parents_snapshots = get_all_ancestry(snapshot)
        checking_points_list =[]
        for checking_snapshot in parents_snapshots:
            checking_points_list.append('%s' % \
                    checking_snapshot.get_checking_point())
    
        original_checking_points = self.get_original_checking_points()
        checking_points_list.extend(original_checking_points)
        return checking_points_list

    def set_original_checking_points(self, original_checking_points):
        '''
        The volume is created from template, while the template was generated
        by another snapshot. So need to add previous snapshot's checking points.

        This function will automatically called when add_volume() is called. 
        So tester doesn't need to call it, unless there are some additional
        checking points, which is not generated from snapshot uuid function.
        '''
        self.original_checking_points = original_checking_points

    def get_original_checking_points(self):
        return self.original_checking_points

    def get_snapshot_list(self):
        return self.snapshot_list

    def set_utility_vm(self, utility_vm):
        self.utility_vm = utility_vm

    def get_utility_vm(self):
        return self.utility_vm

    def set_target_volume(self, target_volume):
        self.target_volume = target_volume
        self.set_original_checking_points(target_volume.get_original_checking_points())
        if target_volume.get_volume().type == volume_header.ROOT_VOLUME:
            self.set_volume_type(volume_header.ROOT_VOLUME)
        else:
            self.set_volume_type(volume_header.DATA_VOLUME)

    def get_target_volume(self):
        return self.target_volume

    def get_current_snapshot(self):
        return self.current_snapshot

    def get_snapshot_head(self):
        return self.snapshot_head

    def _remove_checking_file(self):
        import tempfile
        with tempfile.NamedTemporaryFile() as script:
            script.write('''
device=/dev/`ls -ltr --file-type /dev | grep disk | awk '{print $NF}' | grep -v '[[:digit:]]' | tail -1`1
mkdir -p %s
mount $device %s || exit 1
/bin/rm -rf %s
umount %s
            ''' % (test_lib.WOODPECKER_MOUNT_POINT, \
                    test_lib.WOODPECKER_MOUNT_POINT, \
                    checking_point_folder, \
                    test_lib.WOODPECKER_MOUNT_POINT))
            script.flush()
            if not test_lib.lib_execute_shell_script_in_vm(\
                    self.utility_vm.get_vm(),
                    script.name):
                test_util.test_logger('cleanup checking point failed. It might be because there is not any partition in the target volume. It is harmless.')

    def _cleanup_previous_checking_point(self):
        if not self.get_utility_vm():
            return

        if not self.get_target_volume():
            return

        test_util.test_logger('cleanup checking point files for target volume: %s' % self.get_target_volume())
        volume_obj = self.get_target_volume()
        volume = volume_obj.get_volume()
        if volume.type == 'Root':
            test_util.test_logger('Can not add checking point file for Root Volume: %s, since it can not be detached and reattached to utility vm for checking.' % volume.uuid)
            return

        volume_vm = volume_obj.get_target_vm()
        #check if volume has been attached to the living VM.
        if volume_obj.get_state() == volume_header.ATTACHED:
            if volume_vm.get_state() == vm_header.STOPPED or \
                    volume_vm.get_state() == vm_header.RUNNING:
                #test_util.test_logger('volume has been attached to living VM.')
                volume_obj.detach()
                volume_obj.attach(self.utility_vm)
                self._remove_checking_file()
                volume_obj.detach()
                volume_obj.attach(volume_vm)
                return 

        volume_obj.attach(self.utility_vm)
        self._remove_checking_file()
        volume_obj.detach()

    def create_snapshot(self, name = None):
        if not self.target_volume:
            test_util.test_fail(
                    'Can not create snapshot, before set target_volume')

        if not self.utility_vm:
            test_util.test_fail(
'Can not create snapshot, before set utility_vm, which will be used for doing \
        snapshot checking.')

        sp_option = test_util.SnapshotOption()
        sp_option.set_name(name)
        sp_option.set_volume_uuid(self.target_volume.get_volume().uuid)
        snapshot = ZstackTestSnapshot()
        snapshot.set_snapshot_creation_option(sp_option)
        snapshot.set_utility_vm(self.utility_vm)
        snapshot.set_target_volume(self.target_volume)
        snapshot.create()
        self.add_snapshot(snapshot)
        return snapshot

    def use_snapshot(self, snapshot):
        if self.target_volume.get_state() == volume_header.DELETED \
                or self.target_volume.get_state() == volume_header.EXPUNGED:
            test_util.test_fail(
            'Can not use [snapshot:] %s, as [target_volume:] %s is deleted' \
                    % (snapshot.get_snapshot().uuid, \
                    self.target_volume.get_volume().uuid))

        self.current_snapshot = snapshot
        snapshot.use()

    def add_snapshot(self, snapshot):
        '''
        Called by self.create() or called by test case after manually create 
        ZstackTestSnapshot()
        '''
        self.snapshot_list.append(snapshot)
        self.primary_snapshots.append(snapshot)
        if not self.state:
            self.state = sp_header.CREATED

        if not self.snapshot_head:
            self.current_snapshot = snapshot
            self.snapshot_head = snapshot
            snapshot.set_checking_points(self.get_checking_points(snapshot))
            return

        snapshot.set_parent(self.current_snapshot)
        self.current_snapshot.add_child(snapshot)
        self.current_snapshot = snapshot
        snapshot.set_checking_points(self.get_checking_points(snapshot))

    def delete_snapshot(self, snapshot):
        snapshot.delete()
        if snapshot in self.primary_snapshots:
            self.primary_snapshots.remove(snapshot)
        if snapshot in self.backuped_snapshots:
            self.backuped_snapshots.remove(snapshot)

        #only Hypervisor based snapshot will clean child
        if 'Storage' == snapshot.get_snapshot().type:
            self._update_delete()
            return 

        sp_list = get_snapshot_family(snapshot)
        for sp in sp_list:
            if sp.get_state() == sp_header.DELETED:
                continue
            sp.delete2()
            if sp in self.primary_snapshots:
                self.primary_snapshots.remove(sp)
            if sp in self.backuped_snapshots:
                self.backuped_snapshots.remove(sp)

        self._update_delete()

    def delete(self):
        if self.snapshot_head:
            self.delete_snapshot(self.snapshot_head)

    def backup_snapshot(self, snapshot):
        snapshot.backup()
        self.backuped_snapshots.append(snapshot)
        self.state = sp_header.BACKUPED

    def delete_backuped_snapshot(self, snapshot):
        snapshot.delete_from_backup_storage()
        self.backuped_snapshots.remove(snapshot)
        self._update_delete()

    def _update_delete(self):
        for sp in list(self.snapshot_list):
            if not sp in self.primary_snapshots \
                    and not sp in self.backuped_snapshots:
                self.snapshot_list.remove(sp)

        if not self.backuped_snapshots:
            if not self.primary_snapshots:
                self.state = sp_header.DELETED
            else:
                self.state = sp_header.CREATED
        else:
            if not self.primary_snapshots:
                self.state = sp_header.PS_DELETED
            else:
                self.state = sp_header.BACKUPED

    def check(self):
        import zstackwoodpecker.zstack_test.checker_factory as checker_factory
        self.update()
        if self.state == sp_header.DELETED:
            test_util.test_logger('Volume Snapshot has been deleted. Does not need to execute check() function')
            return
        checker = checker_factory.CheckerFactory().create_checker(self)
        checker.check()

    def update(self):
        if self.get_target_volume().get_state() == volume_header.DELETED:
            #since volume is deleted, can't create next snapshot, then
            #the current snapshot is useless. 
            self.current_snapshot = None
            #TODO: In current zstack, if volume is deleted, all sp in ps will 
            #be removed. Should update this, after new delete sp API is added.
            self.primary_snapshots = []

        #In case, test case might directly call ZstackTestSnapshot().* API
        # need to manually update each sp. And if sp's parent is deleted, this
        # SP is also needed to be deleted. 
        for sp in self.snapshot_list:
            sp.update()
            if sp.get_state() == sp_header.DELETED:
                if sp in self.primary_snapshots:
                    self.primary_snapshots.remove(sp)
                if sp in self.backuped_snapshots:
                    self.backuped_snapshots.remove(sp)

        self._update_delete()

    def get_primary_snapshots(self):
        return self.primary_snapshots

    def get_backuped_snapshots(self):
        return self.backuped_snapshots

class ZstackTestSnapshot(sp_header.TestSnapshot):
    def __init__(self):
        self.snapshot_option = test_util.SnapshotOption()
        self.parent = None
        self.child_list = []
        self.checking_point = uuid.uuid1().get_hex()
        #utility_vm is mostly like a VR vm, which could be connected by ssh.
        self.utility_vm = None
        self.image_option = None
        #all checking points files including parents checking points.
        self.checking_points = []
        super(ZstackTestSnapshot, self).__init__()

    def set_checking_points(self, checking_points):
        self.checking_points = checking_points

    def get_checking_points(self):
        return self.checking_points

    def _live_snapshot_cap_check(self):
        '''
        Deprecated. It is not recommended to be called in create_snapshot.
        '''
        volume_obj = self.get_target_volume()
        volume_vm = volume_obj.get_target_vm()
        if volume_vm and volume_vm.get_state() == vm_header.RUNNING:
            host = test_lib.lib_find_host_by_vm(volume_vm.get_vm())
            conditions = res_ops.gen_query_conditions('tag', '=', \
                    'capability:liveSnapshot')
            tag_info = test_lib.lib_find_host_tag(host, conditions)
            if tag_info:
                test_util.test_logger('host: %s support live snapshot' % \
                        host.uuid)
                return True
            else:
                test_util.test_fail('host: %s does not support live snapshot' \
                        % host.uuid)
                return False

        return True

    def create(self):
        '''
        Not recommended to be called by test case directly. Test case needs to
        call ZstackVolumeSnapshot.create_snapshot()
        '''
        super(ZstackTestSnapshot, self).create()
        if not self.target_volume:
            test_util.test_fail('Can not create snapshot, before set target_volume')
        if not self.utility_vm:
            test_util.test_fail('Can not create snapshot, before set utility_vm, which will be used for doing snapshot checking. utiltiy_vm is mostly like a VR vm.')
        #self._live_snapshot_cap_check()
        self.add_checking_point()
        self.snapshot = vol_ops.create_snapshot(self.snapshot_option)
        self.target_volume.update_volume()

    def add_checking_point(self):
        volume_obj = self.get_target_volume()
        volume = volume_obj.get_volume()
        if volume.type == 'Root':
            test_util.test_logger('Can not add checking point file for Root Volume: %s, since it can not be detached and reattached to utility vm for checking.' % volume.uuid)
            return

        volume_vm = volume_obj.get_target_vm()
        #check if volume has been attached to the living VM.
        if volume_obj.get_state() == volume_header.ATTACHED:
            if volume_vm.get_state() == vm_header.STOPPED or \
                    volume_vm.get_state() == vm_header.RUNNING:
                test_util.test_logger('volume has been attached to living VM.')

                volume_obj.detach()
                volume_obj.attach(self.utility_vm)
                #add checking point
                self._create_checking_file()
                volume_obj.detach()
                volume_obj.attach(volume_vm)
                return 
        volume_obj.attach(self.utility_vm)
        #add_checking_point
        self._create_checking_file()
        volume_obj.detach()

    def _create_checking_file(self):
        #make fs for volume, if it doesn't exist
        if not self.parent and not self.child_list:
            test_lib.lib_mkfs_for_volume(self.target_volume.get_volume().uuid, \
                    self.utility_vm.get_vm())

        import tempfile
        with tempfile.NamedTemporaryFile() as script:
            script.write('''
device=/dev/`ls -ltr --file-type /dev | grep disk | awk '{print $NF}' | grep -v '[[:digit:]]' | tail -1`1
mkdir -p %s
mount $device %s
mkdir -p %s
touch %s/%s
umount %s
            ''' % (test_lib.WOODPECKER_MOUNT_POINT, \
                    test_lib.WOODPECKER_MOUNT_POINT, \
                    checking_point_folder, checking_point_folder, \
                    self.checking_point, test_lib.WOODPECKER_MOUNT_POINT))
            script.flush()
            test_lib.lib_execute_shell_script_in_vm(self.utility_vm.get_vm(),
                    script.name)

        if self.parent:
            test_util.test_logger('[snapshot:] %s checking file: %s is created.\
Its [parent:] %s' % \
                    (self.snapshot_option.get_name(), \
                        self.checking_point, self.parent.get_snapshot().uuid))
        else:
            test_util.test_logger('[snapshot:] %s checking file: %s is created.'% (self.snapshot_option.get_name(), self.checking_point))

    def delete(self):
        '''
        Not recommended to be directly called by test case. Test case needs to
        call ZstackVolumeSnapshot.delete_snapshot()
        '''
        vol_ops.delete_snapshot(self.snapshot.uuid)
        self.delete2()

    def delete2(self):
        super(ZstackTestSnapshot, self).delete()

    def backup(self, backup_storage_uuid = None):
        '''
        Not recommended to be directly called by test case. Test case needs to
        call ZstackVolumeSnapshot.backup_snapshot()
        '''
        self.snapshot = vol_ops.backup_snapshot(self.get_snapshot().uuid, backup_storage_uuid)
        super(ZstackTestSnapshot, self).backup()

    def use(self):
        '''
        Not recommended to be directly called by test case. Test case needs to
        call ZstackVolumeSnapshot.use_snapshot()
        '''
        if self.target_volume.get_state() == volume_header.DELETED:
            test_util.test_fail(
'Should not be called, as snapshot volume:%s has been deleted. Snapshot can not\
be applied to volume' % self.target_volume.get_volume().uuid)

        vol_ops.use_snapshot(self.get_snapshot().uuid)
        super(ZstackTestSnapshot, self).use()
        #volume installPath will be changed, so need to update volume
        self.target_volume.update_volume()

    def delete_from_primary_storage(self):
        '''
        Not recommended to be directly called by test case. Test case needs to
        call ZstackVolumeSnapshot.delete_snapshot_from_primary_storage()
        '''
        super(ZstackTestSnapshot, self).delete_from_primary_storage()

    def delete_from_backup_storage(self):
        '''
        Not recommended to be directly called by test case. Test case needs to
        call ZstackVolumeSnapshot.delete_backuped_snapshot()
        '''
        vol_ops.delete_snapshot_from_backupstorage(self.get_snapshot().uuid)
        super(ZstackTestSnapshot, self).delete_from_backup_storage()

    def create_data_volume(self, name = None, ps_uuid = None):
        '''
        @return: zstack_test_volume() object 
        '''
        import zstackwoodpecker.zstack_test.zstack_test_volume as \
                zstack_volume_header

        if self.state == sp_header.DELETED:
            test_util.test_fail(
'Should not be called, as snapshot volume:%s has been deleted. Snapshot can not\
be created to a new data volume' % self.target_volume.get_volume().uuid)

        if not name:
            name = 'data volume created by sp: %s' % self.snapshot.uuid

        snapshot_uuid = self.get_snapshot().uuid
        volume_inv = vol_ops.create_volume_from_snapshot(snapshot_uuid, \
                name, ps_uuid)
        super(ZstackTestSnapshot, self).create_data_volume()

        volume_obj = zstack_volume_header.ZstackTestVolume()
        volume_obj.set_volume(volume_inv)
        volume_obj.set_state(volume_header.DETACHED)
        #ROOT Volume won't create checking point. So skip.
        if self.get_volume_type() != volume_header.ROOT_VOLUME:
            volume_obj.set_original_checking_points(self.get_checking_points())
        return volume_obj

    def create_image_template(self):
        '''
        @return: zstack_test_image() object 
        '''
        import zstackwoodpecker.zstack_test.zstack_test_image as \
                zstack_image_header
        if self.state == sp_header.DELETED:
            test_util.test_fail(\
'Should not be called, as snapshot volume:%s has been deleted. Snapshot can \
not be created to a new template' % \
                    self.target_volume.get_volume().uuid)

        if not self.image_option.get_root_volume_uuid():
            self.image_option.set_root_volume_uuid(self.snapshot.uuid)

        if not self.image_option.get_backup_storage_uuid_list():
            bs_uuid = res_ops.get_resource(res_ops.BACKUP_STORAGE)[0].uuid
            self.image_option.set_backup_storage_uuid_list([bs_uuid])

        img_inv = img_ops.create_template_from_snapshot(self.image_option)
        super(ZstackTestSnapshot, self).create_image_template()

        img_obj = zstack_image_header.ZstackTestImage()
        img_obj.set_image(img_inv)
        img_obj.set_state(image_header.CREATED)
        #ROOT Volume won't create checking point. So skip.
        if self.get_volume_type() != volume_header.ROOT_VOLUME:
            img_obj.set_original_checking_points(self.get_checking_points())
        return img_obj

    def set_snapshot_creation_option(self, snapshot_option):
        self.snapshot_option = snapshot_option

    def get_snapshot_creation_option(self):
        return self.snapshot_option

    def set_image_creation_option(self, image_option):
        self.image_option = image_option

    def get_image_creation_option(self):
        return self.image_option

    def get_checking_point(self):
        return self.checking_point

    def set_utility_vm(self, utility_vm):
        self.utility_vm = utility_vm

    def get_utility_vm(self):
        return self.utility_vm

    def set_parent(self, parent):
        self.parent = parent

    def get_parent(self):
        return self.parent

    def add_child(self, snapshot):
        self.child_list.append(snapshot)

    def get_child_list(self):
        return self.child_list

    def rm_child(self, snapshot):
        self.child_list.remove(snapshot)

    def update(self):
        if self.get_target_volume().state == volume_header.DELETED \
                or self.get_target_volume().state == volume_header.EXPUNGED:
            super(ZstackTestSnapshot, self).delete_from_primary_storage()

    def check(self):
        '''
        Should not be called by test cases
        '''
        super(ZstackTestSnapshot, self).check()
