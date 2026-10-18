"""Independent response metadata oracle, using published disposable scalar2."""
import hashlib
import json
from pathlib import Path
import unittest

import secp256k1
from scripts import verify_specs as v


ROOT = Path(__file__).resolve().parents[1]
USER = 'c6047f9441ed7d6d3045406e95c07cd85c778e4b8cef3ca7abac09b95c709ee5'


class ResponseIdentityTests(unittest.TestCase):
    def step(self, signed=False):
        name = 'sign-event-response-step' if signed else 'get-public-key-response-step'
        step = json.loads((ROOT/f'vectors/nip46-relay-steps/{name}.json').read_text())
        step['format'] = 'nsealr-nip46-relay-response-step-v1'
        step['expected_user_pubkey'] = USER
        if signed:
            event = {'pubkey':USER, 'created_at':1710000000, 'kind':1, 'tags':[], 'content':'independent user event'}
            canonical = json.dumps([0,USER,1710000000,1,[],'independent user event'],separators=(',',':'))
            event['id'] = hashlib.sha256(canonical.encode()).hexdigest()
            key = secp256k1.PrivateKey(bytes.fromhex('00'*31+'02'),raw=True)
            self.assertEqual(key.pubkey.serialize()[1:].hex(),USER)
            event['sig'] = key.schnorr_sign(bytes.fromhex(event['id']),'',raw=True).hex()
            step['decrypted_message']['result'] = json.dumps(event,separators=(',',':'))
        else:
            step['decrypted_message']['result'] = USER
        return step

    def evaluate(self, step):
        errors=[]
        result=v.expected_nip46_relay_response_step('independent-v1',step,errors)
        return result,errors

    def test_distinct_user_public_key(self):
        step=self.step();self.assertNotEqual(USER,step['event']['pubkey'])
        result,errors=self.evaluate(step)
        self.assertEqual(errors,[]);self.assertIsNotNone(result)
        self.assertEqual(result['result_pubkey'],USER)
        self.assertIs(result['result_pubkey_bound_to_expected_user'],True)

    def test_distinct_inner_author_signature(self):
        result,errors=self.evaluate(self.step(True))
        self.assertEqual(errors,[]);self.assertIsNotNone(result)
        self.assertIs(result['signed_event_signature_verified'],True)
        self.assertEqual(result['result_pubkey'],USER)

    def test_missing_expected_user_is_unbound(self):
        step=self.step();del step['expected_user_pubkey']
        result,errors=self.evaluate(step)
        self.assertEqual(errors,[]);self.assertIs(result['result_pubkey_bound_to_expected_user'],False)

    def test_expected_user_mismatch_and_invalid_shape(self):
        for key in ['f'*64,'not-a-public-key',None]:
            with self.subTest(key=key):
                step=self.step();step['expected_user_pubkey']=key
                result,errors=self.evaluate(step)
                self.assertIsNone(result);self.assertTrue(errors)

    def test_invalid_inner_signature_and_id(self):
        for field,value in [('sig','00'*64),('id','00'*32)]:
            with self.subTest(field=field):
                step=self.step(True);event=json.loads(step['decrypted_message']['result']);event[field]=value
                step['decrypted_message']['result']=json.dumps(event,separators=(',',':'))
                result,errors=self.evaluate(step)
                self.assertIsNone(result);self.assertTrue(errors)

    def test_invalid_outer_signature(self):
        step=self.step();step['event']['sig']='00'*64
        result,errors=self.evaluate(step)
        self.assertIsNone(result);self.assertTrue(errors)

    def test_signed_outer_boolean_timestamp_is_not_an_integer(self):
        for timestamp in (True, False):
            with self.subTest(timestamp=timestamp):
                step = self.step()
                event = step['event']
                event['pubkey'] = USER
                event['created_at'] = timestamp
                canonical = json.dumps(
                    [0, USER, timestamp, event['kind'], event['tags'], event['content']],
                    separators=(',', ':'), ensure_ascii=False,
                )
                event['id'] = hashlib.sha256(canonical.encode()).hexdigest()
                key = secp256k1.PrivateKey(bytes.fromhex('00' * 31 + '02'), raw=True)
                event['sig'] = key.schnorr_sign(bytes.fromhex(event['id']), '', raw=True).hex()
                result, errors = self.evaluate(step)
                self.assertIsNone(result)
                self.assertTrue(any('created_at must be a safe non-negative integer' in e for e in errors))

    def test_same_key_control(self):
        step=json.loads((ROOT/'vectors/nip46-relay-steps/get-public-key-response-step.json').read_text())
        step['format']='nsealr-nip46-relay-response-step-v1'
        step['expected_user_pubkey']=step['event']['pubkey']
        result,errors=self.evaluate(step)
        self.assertEqual(errors,[]);self.assertIs(result['result_pubkey_bound_to_expected_user'],True)

    def test_digit_only_metadata_key_is_not_a_json_number(self):
        step=self.step();step['decrypted_message']['result']='1'*64;step.pop('expected_user_pubkey')
        result,errors=self.evaluate(step)
        self.assertEqual(errors,[]);self.assertEqual(result['result_pubkey'],'1'*64)
        self.assertIs(result['result_pubkey_bound_to_expected_user'],False)

    def test_duplicate_escaped_member_never_disappears_before_check(self):
        for fragment in ['"pubkey":"'+USER+'",','"pub\\u006bey":"'+USER+'",']:
            step=self.step(True);raw=step['decrypted_message']['result']
            step['decrypted_message']['result']='{'+fragment+raw[1:]
            result,errors=self.evaluate(step)
            self.assertIsNone(result);self.assertTrue(errors)

    def test_depth_byte_and_trailing_limits(self):
        for raw in ['['*33+'null'+']'*33,'"'+'é'*512+'"','null true','NaN']:
            with self.subTest(raw=raw[:12]):
                step=self.step();step['decrypted_message']['result']=raw
                result,errors=self.evaluate(step)
                self.assertIsNone(result);self.assertTrue(errors)

    def test_exact_json_comparator(self):
        self.assertTrue(v.exact_json_equal({'a':True,'b':[1,2]},{'b':[1,2],'a':True}))
        for other in [{'a':1,'b':[1,2]},{'a':True,'b':[2,1]},{'a':True},{'a':True,'b':[1,2],'c':None}]:
            self.assertFalse(v.exact_json_equal({'a':True,'b':[1,2]},other))


if __name__=='__main__':
    unittest.main()
