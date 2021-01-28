from libcloud.compute.providers import get_driver, set_driver

set_driver('CTyun', 'libcloud_mods.ctyun', 'CTyunNodeDriver')

driver = get_driver('CTyun')
CTyunDriver = driver(access_key, secret_key)
