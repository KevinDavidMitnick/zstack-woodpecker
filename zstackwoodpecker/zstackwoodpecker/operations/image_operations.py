'''

Image (Root Volume) Template operations for test.

@author: Youyk
'''

import apibinding.api_actions as api_actions
import zstackwoodpecker.test_util as test_util
import account_operations
import resource_operations as res_ops

def add_data_volume_template(image_option):
    action = api_actions.AddImageAction()
    action.name = image_option.get_name()
    action.url = image_option.get_url()
    action.mediaType = 'DataVolumnTemplate'
    if image_option.get_mediaType() and \
            action.mediaType != image_option.get_mediaType():
        test_util.test_warn('image type %s was not %s' % \
                (image_option.get_mediaType(), action.mediaType))

    action.format = image_option.get_format()
    action.backupStorageUuids = image_option.get_backup_stroage_list()
    test_util.action_logger('Add [Volume:] %s from [url:] %s ' % (action.name, action.url))
    evt = account_operations.execute_action_with_session(action, image_option.get_session_uuid())

    test_util.test_logger('[volume:] %s is added.' % evt.inventory.uuid)
    return evt.inventory

def add_iso_template(image_creation_option):
    '''
    Add iso template
    '''
    action = api_actions.AddImageAction()
    action.name = image_creation_option.get_name()
    action.guest_os_type = image_creation_option.get_guest_os_type()
    action.mediaType = 'ISO'

    action.backupStorageUuids = \
            image_creation_option.get_backup_storage_uuid_list()
    action.bits = image_creation_option.get_bits()
    action.description = image_creation_option.get_description()
    action.format = 'iso'
    action.url = image_creation_option.get_url()
    action.timeout = image_creation_option.get_timeout()
    test_util.action_logger('Add ISO Template from url: %s in [backup Storage:] %s' % (action.url, action.backupStorageUuids))
    evt = account_operations.execute_action_with_session(action, \
            image_creation_option.get_session_uuid())
    return evt.inventory

def add_root_volume_template(image_creation_option):
    '''
    Add root volume template
    '''
    action = api_actions.AddImageAction()
    action.name = image_creation_option.get_name()
    action.guest_os_type = image_creation_option.get_guest_os_type()
    action.mediaType = 'RootVolumeTemplate'
    if image_creation_option.get_mediaType() and \
            action.mediaType != image_creation_option.get_mediaType():
        test_util.test_warn('image type %s was not %s' % \
                (image_creation_option.get_mediaType(), action.mediaType))

    action.backupStorageUuids = \
            image_creation_option.get_backup_storage_uuid_list()
    action.bits = image_creation_option.get_bits()
    action.description = image_creation_option.get_description()
    action.format = image_creation_option.get_format()
    action.url = image_creation_option.get_url()
    action.timeout = image_creation_option.get_timeout()
    test_util.action_logger('Add Root Volume Template from url: %s in [backup Storage:] %s' % (action.url, action.backupStorageUuids))
    evt = account_operations.execute_action_with_session(action, \
            image_creation_option.get_session_uuid())
    return evt.inventory

def create_root_volume_template(image_creation_option):
    '''
    Create Root Volume Template from a root volume
    '''
    action = api_actions.CreateRootVolumeTemplateFromRootVolumeAction()
    action.rootVolumeUuid = image_creation_option.get_root_volume_uuid()
    action.backupStorageUuids = image_creation_option.get_backup_storage_uuid_list()

    name = image_creation_option.get_name()
    if not name:
        action.name = 'test_template_image'
    else:
        action.name = name

    action.guestOsType = image_creation_option.get_guest_os_type()
    action.system = image_creation_option.get_system()
    action.platform = image_creation_option.get_platform()

    description = image_creation_option.get_description()
    if not description:
        action.description = "test create template from volume"
    else:
        action.description = description

    test_util.action_logger('Create Image Template from [root Volume:] %s in [backup Storage:] %s' % (action.rootVolumeUuid, action.backupStorageUuids))
    evt = account_operations.execute_action_with_session(action, image_creation_option.get_session_uuid())
    return evt.inventory

def delete_image(image_uuid, backup_storage_uuid_list=None, session_uuid=None):
    action = api_actions.DeleteImageAction()
    action.uuid = image_uuid
    action.backupStorageUuids = backup_storage_uuid_list
    test_util.action_logger('Delete [image:] %s' % image_uuid)
    evt = account_operations.execute_action_with_session(action, session_uuid)
    return evt

def expunge_image(image_uuid, backup_storage_uuid_list=None, session_uuid=None):
    action = api_actions.ExpungeImageAction()
    action.imageUuid = image_uuid
    action.backupStorageUuids = backup_storage_uuid_list
    test_util.action_logger('Expunge [image:] %s' % image_uuid)
    evt = account_operations.execute_action_with_session(action, session_uuid)
    return evt

def create_template_from_snapshot(image_creation_option, session_uuid=None):
    action = api_actions.CreateRootVolumeTemplateFromVolumeSnapshotAction()
    action.snapshotUuid = image_creation_option.get_root_volume_uuid()
    action.backupStorageUuids = image_creation_option.get_backup_storage_uuid_list()

    action.guestOsType = image_creation_option.get_guest_os_type()
    action.system = image_creation_option.get_system()
    action.platform = image_creation_option.get_platform()

    name = image_creation_option.get_name()
    if not name:
        action.name = 'test_template_image_by_snapshot'
    else:
        action.name = name


    description = image_creation_option.get_description()
    if not description:
        action.description = "test create template from snapshot: %s" % \
                action.snapshotUuid
    else:
        action.description = description

    test_util.action_logger('Create Image Template from [snapshot:] %s in [backup Storage:] %s' % (action.snapshotUuid, action.backupStorageUuids))
    evt = account_operations.execute_action_with_session(action, image_creation_option.get_session_uuid())
    return evt.inventory

def reconnect_sftp_backup_storage(bs_uuid, session_uuid = None):
    action = api_actions.ReconnectSftpBackupStorageAction()
    action.uuid = bs_uuid
    action.timeout = 120000
    test_util.action_logger('Reconnect Sftp Backup Storage [uuid:] %s' % bs_uuid)
    evt = account_operations.execute_action_with_session(action, session_uuid)
    return evt.inventory
