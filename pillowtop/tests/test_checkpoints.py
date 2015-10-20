from django.test import SimpleTestCase, override_settings
import time
from pillowtop.checkpoints.manager import PillowCheckpointManager, PillowCheckpoint
from pillowtop.checkpoints.util import get_machine_id
from pillowtop.dao.mock import MockDocumentStore
from pillowtop.exceptions import PillowtopCheckpointReset


class PillowCheckpointTest(SimpleTestCase):

    def setUp(self):
        self._checkpoint_id = 'test-checkpoint-id'
        self._dao = MockDocumentStore()
        self._checkpoint = PillowCheckpoint(self._dao, self._checkpoint_id)

    @override_settings(PILLOWTOP_MACHINE_ID='test-ptop')
    def test_get_machine_id_settings(self):
        self.assertEqual('test-ptop', get_machine_id())

    def test_get_machine_id(self):
        # since this is machine dependent just ensure that this returns something
        # and doesn't crash
        self.assertTrue(bool(get_machine_id()))

    def test_get_or_create_empty(self):
        checkpoint_manager = PillowCheckpointManager(MockDocumentStore())
        checkpoint = checkpoint_manager.get_or_create_checkpoint('some-id')
        self.assertEqual('0', checkpoint['seq'])
        self.assertTrue(bool(checkpoint['timestamp']))

    def test_checkpoint_id(self):
        self.assertEqual(self._checkpoint_id, self._checkpoint.checkpoint_id)

    def test_create_initial_checkpoint(self):
        checkpoint = self._checkpoint.get_or_create()
        self.assertEqual('0', checkpoint['seq'])

    def test_db_changes_returned(self):
        self._checkpoint.get_or_create()
        self._dao.save_document(self._checkpoint_id, {'seq': '1'})
        checkpoint = self._checkpoint.get_or_create()
        self.assertEqual('1', checkpoint['seq'])

    def test_verify_unchanged_ok(self):
        self._checkpoint.get_or_create()
        checkpoint = self._checkpoint.get_or_create(verify_unchanged=True)
        self.assertEqual('0', checkpoint['seq'])

    def test_verify_unchanged_fail(self):
        self._checkpoint.get_or_create()
        self._dao.save_document(self._checkpoint_id, {'seq': '1'})
        with self.assertRaises(PillowtopCheckpointReset):
            self._checkpoint.get_or_create(verify_unchanged=True)

    def test_update(self):
        self._checkpoint.get_or_create()
        for seq in ['1', '5', '22']:
            self._checkpoint.update_to(seq)
            self.assertEqual(seq, self._checkpoint.get_or_create()['seq'])

    def test_update_verify_unchanged_fail(self):
        self._checkpoint.get_or_create()
        self._dao.save_document(self._checkpoint_id, {'seq': '1'})
        with self.assertRaises(PillowtopCheckpointReset):
            self._checkpoint.update_to('2')

    def test_touch_checkpoint_noop(self):
        timestamp = self._checkpoint.get_or_create()['timestamp']
        self._checkpoint.touch(min_interval=10)
        timestamp_back = self._checkpoint.get_or_create()['timestamp']
        self.assertEqual(timestamp_back, timestamp)

    def test_touch_checkpoint_update(self):
        timestamp = self._checkpoint.get_or_create()['timestamp']
        time.sleep(.1)
        self._checkpoint.touch(min_interval=0)
        timestamp_back = self._checkpoint.get_or_create()['timestamp']
        self.assertNotEqual(timestamp_back, timestamp)
