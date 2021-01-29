import hashlib

def md5(access_key='', secret_key='', *args):
    """
    :param access_key: accesskey
    :param secret_key: secretKey
    :param args: other post params
    :return: md5 encoded vkey
    """
    m2 = hashlib.md5()
    vkey = '' + access_key
    for param in args:
        if not isinstance(param, str): 
            param = str(param)
        vkey = vkey + '_' + param

    vkey = vkey + '_' + secret_key
    m2.update(vkey.encode('utf-8'))
    # print vkey
    print(m2.hexdigest())
    return m2.hexdigest()
