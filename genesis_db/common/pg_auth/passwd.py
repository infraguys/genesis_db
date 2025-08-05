#    Copyright 2025 Genesis Corporation.
#
#    All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import base64
import hashlib
import hmac
import re
from secrets import token_bytes

from genesis_db.common.pg_auth import saslprep


def verify_password(role, password, verifier, method="scram-sha-256"):
    """
    Test the given password against the verifier.

    The given password may already be a verifier, in which case test for
     simple equality.

    Ported from Salt.
    """
    if method == "md5" or method is True:
        if password.startswith("md5"):
            expected = password
        else:
            expected = _md5_password(role, password)
    elif method == "scram-sha-256":
        if password.startswith("SCRAM-SHA-256"):
            expected = password
        else:
            match = re.match(r"^SCRAM-SHA-256\$(\d+):([^\$]+?)\$", verifier)
            if match:
                iterations = int(match.group(1))
                salt_bytes = base64.b64decode(match.group(2))
                expected = scram_sha_256(
                    password, salt_bytes=salt_bytes, iterations=iterations
                )
            else:
                expected = object()
    elif method is False:
        expected = password
    else:
        expected = object()

    return verifier == expected


def _md5_password(role, password):
    return "md5{}".format(
        hashlib.md5(f"{password}{role}".encode("utf-8")).hexdigest()  # nosec
    )


def scram_sha_256(password, salt_bytes=None, iterations=4096):
    """
    Build a SCRAM-SHA-256 password verifier.

    Ported from https://doxygen.postgresql.org/scram-common_8c.html
    """
    if salt_bytes is None:
        salt_bytes = token_bytes(16)
    password = saslprep.saslprep(password).encode("utf-8")
    salted_password = hashlib.pbkdf2_hmac(
        "sha256", password, salt_bytes, iterations
    )
    stored_key = hmac.new(salted_password, b"Client Key", "sha256").digest()
    stored_key = hashlib.sha256(stored_key).digest()
    server_key = hmac.new(salted_password, b"Server Key", "sha256").digest()
    return "SCRAM-SHA-256${}:{}${}:{}".format(
        iterations,
        base64.b64encode(salt_bytes).decode("ascii"),
        base64.b64encode(stored_key).decode("ascii"),
        base64.b64encode(server_key).decode("ascii"),
    )
