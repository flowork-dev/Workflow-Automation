#######################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\get_ip.py JUMLAH BARIS 24 
#######################################################################

import socket
def get_local_ip():
    """
    Menemukan alamat IP lokal mesin.
    Menyambung ke server eksternal untuk menemukan antarmuka jaringan yang disukai.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"  # Fallback jika tidak ada koneksi
    finally:
        s.close()
    return ip
if __name__ == "__main__":
    print(get_local_ip())
