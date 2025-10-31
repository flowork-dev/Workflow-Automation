#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\flowork_kernel\utils\flowchain_verifier.py JUMLAH BARIS 75 
#######################################################################

import json
import hashlib
import os
from web3.auto import w3
from eth_account.messages import encode_defunct
def calculate_hash(file_path):
    """Calculates the SHA-256 hash of a file."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        return sha256.hexdigest()
    except IOError:
        return None
def verify_workflow_chain(workflow_directory):
    """
    Verifies the entire history chain of a workflow,
    from the newest version down to the first.
    (PERBAIKAN) Logika verifikasi tanda tangan disesuaikan agar cocok
    dengan apa yang ditandatangani oleh klien (GUI).
    """
    if not os.path.isdir(workflow_directory):
        print(f"[Verifier] Directory not found: {workflow_directory}") # English Hardcode
        return False, f"Directory not found: {workflow_directory}"
    try:
        files = sorted(
            [f for f in os.listdir(workflow_directory) if f.endswith('.json') and f.startswith('v')],
            key=lambda f: int(f.split('_')[0][1:]) # Urutkan berdasarkan nomor versi
        )
    except FileNotFoundError:
        print(f"[Verifier] Directory not found during list: {workflow_directory}") # English Hardcode
        return False, f"Directory not found: {workflow_directory}"
    except Exception as e:
        print(f"[Verifier] Failed to sort version files: {e}") # English Hardcode
        return False, f"Failed to sort version files: {e}"
    if not files:
        print(f"[Verifier] No version files found in: {workflow_directory}") # English Hardcode
        return True, "No versions found, chain is valid by default." # Empty is valid
    previous_file_hash = None
    for i, filename in enumerate(files):
        file_path = os.path.join(workflow_directory, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            signature = data.get('signature')
            author_id = data.get('author_id')
            workflow_data = data.get('workflow_data')
            if not signature or not author_id or workflow_data is None:
                raise ValueError(f"File {filename} is corrupt: missing signature, author_id, or workflow_data") # English Hardcode
            unsigned_data_block = {"workflow_data": workflow_data}
            message_to_verify = json.dumps(unsigned_data_block, sort_keys=True, separators=(',', ':'))
            encoded_message = encode_defunct(text=message_to_verify)
            recovered_address = w3.eth.account.recover_message(encoded_message, signature=signature)
            if recovered_address.lower() != author_id.lower():
                raise ValueError(f"Invalid signature in version {data.get('version', filename)}. Address mismatch.") # English Hardcode
            if i == 0: # Ini adalah file pertama (v1)
                if data.get('previous_hash') is not None:
                     raise ValueError(f"Chain broken at {filename}: First version file should have null previous_hash.") # English Hardcode
            else: # Ini v2, v3, dst.
                if data.get('previous_hash') != previous_file_hash:
                    raise ValueError(f"Chain broken at {filename}! Hash mismatch. Expected {previous_file_hash}, got {data.get('previous_hash')}") # English Hardcode
            previous_file_hash = calculate_hash(file_path)
        except Exception as e:
            print(f"[Verifier] CRITICAL: Chain verification failed for {filename}: {e}") # English Hardcode
            return False, f"Verification failed for {filename}: {e}"
    print(f"[Verifier] Workflow '{os.path.basename(workflow_directory)}' chain is valid and secure.") # English Hardcode
    return True, "Chain verified."
