import base64

from libcloud.utils.py3 import urlencode
from libcloud.utils.py3 import b
from libcloud.utils.misc import md5

try:
    import simplejson as json
except ImportError:
    import json

from libcloud.common.base import JsonResponse, ConnectionUserAndKey
from libcloud.common.types import MalformedResponseError
from libcloud.compute.providers import Provider
from libcloud.compute.types import InvalidCredsError
from libcloud.compute.base import Node, NodeDriver, StorageVolume
from libcloud.compute.base import NodeSize, NodeImage, NodeLocation

CTYUN_API_HOST = '42.123.120.96'

CTYUN_NODE_STATE = dict(starting=10, running=0, restarting=1,
        stopped=5, stopping=11, restoreing=12, dueed=9)
CTYUN_VOLUME_STATE = {'unbind': 0, 'bind': 2, 'binding': 7, 'unbinding': 9,
        '1': 10, '2': 11}


class CTyunResponse(JsonResponse):
    def parse_body(self):
        try:
            return super(CTyunResponse, self).parse_body()
        except MalformedResponseError:
            return self.body

    def success(self):
        return int(self.status) == 200

    def parse_error(self):
        if int(self.status) == 401:
            if not self.body:
                raise InvalidCredsError(str(self.status) + ": " + self.error)
            else:
                raise InvalidCredsError(self.body)
        return self.body


class CTyunNodeSize(NodeSize):
    def __init__(self, id, name, cpu, ram, disk, price, driver):
        self.id = id
        self.name = name
        self.cpu = cpu
        self.ram = ram
        self.disk = disk
        self.price = price
        self.driver = driver

    def __repr__(self):
        return ('<NodeSize: id=%s, name=%s, cpu=%s, ram=%s, disk=%s, price=%s, driver=%s...>' %
                (self.id, self.name, self.cpu, self.ram, self.disk, self.disk, self.price, self.driver))


class CTyunConnection(ConnectionUserAndKey):
    host = CTYUN_API_HOST
    secure = True
    responseCls = CTyunResponse
    allow_insecure = True

    def add_default_headers(self, headers):
        user_b64 = base64.b64encode(b('%s %s' % (self.user_id, self.key)))
        headers['Authorization'] = 'Basic %s' % user_b64
        return headers


class CTyunNodeDriver(NodeDriver):
    connectionCls = CTyunConnection
    type = Provider.CTYUN
    api_name = 'ctyun'
    name = 'CTyun'

    def __init__(self, key, secret=None, secure=False, host=None, port=None, **kwargs):
        host = host or CTYUN_API_HOST
        self.accesskey = key or ''
        self.screctkey = secret or ''
        super(CTyunNodeDriver, self).__init__(key=key, secret=secret,
                secure=secure,
                host=host, port=port,
                **kwargs)

        # libcloud driver public func #
    def list_nodes(self, page_no=1, page_size=2):
        """
        :param page_no: Page No.
        :param page_size: Page Size
        :return: nodes list
        """
        response_json = self.get_vm_list(page_no=page_no, page_size=page_size)
        vms_json = response_json['returnObj']['VMList']
        nodes = self._to_nodes(vms_json)
        return nodes

    def reboot_node(self, node):
        if node == Node:
            raise Exception("CTyunDriver::reboot_node node is empty")
        response_json = self.restart_vm(node.id)
        return response_json['returnCode'] == 200

    def stop_node(self, node):
        if node == Node:
            raise Exception("CTyunDriver::stop_node node is empty")
        response_json = self.stop_vm(node.id)
        return response_json['returnCode'] == 200

    def start_node(self, node):
        if node == Node:
            raise Exception("CTyunDriver::start_node node is empty")
        response_json = self.start_vm(node.id)
        return response_json['returnCode'] == 200

    def list_volumes(self, zone_id=1, page_no=1, page_size=10):
        response_json = self.get_data_disk_list(zone_id=zone_id, page_no=page_no, page_size=page_size)
        vols_json = response_json['returnObj']['DiskList']
        vols = [self._to_volume(el) for el in vols_json]
        print(vols)
        return vols

    # CTyun func#
    def list_zone(self):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey)
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/loadZoneList', headers=headers, data=data, method='POST')

        return json.loads(result.body)

    def list_vm_type(self):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey)
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/loadVMTypeList', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def list_os(self, zoneid):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, zoneid),
                'zoneId': zoneid
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/loadOSList', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_new_order_price(self, cpu, memory, datahd, os, bw, ordernum, periodtype, periodnum, zoneid):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, cpu, memory, datahd, os, bw, ordernum, periodtype,
                    periodnum, zoneid),
                'cpu': cpu,
                'memory': memory,
                'datahd': datahd,
                'os': os,
                'bw': bw,
                'orderNum': ordernum,
                'periodType': periodtype,
                'periodNum': periodnum,
                'zoneId': zoneid
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/getNewOrderPrice', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def buy_cloud(self, cpu, memory, datahd, os, bw, ordernum, periodtype, periodnum, zoneid):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, cpu, memory, datahd, os, bw, ordernum, periodtype,
                    periodnum, zoneid),
                'cpu': cpu,
                'memory': memory,
                'datahd': datahd,
                'os': os,
                'bw': bw,
                'orderNum': ordernum,
                'periodType': periodtype,
                'periodNum': periodnum,
                'zoneId': zoneid
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/buyCloud', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_renew_order_price(self, periodtype, periodnum, vm_id):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, periodtype, periodnum, vm_id),
                'periodType': periodtype,
                'periodNum': periodnum,
                'id': vm_id
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/getRenewOrderPrice', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def renew_cloud(self, periodtype, periodnum, vm_id):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, periodtype, periodnum, vm_id),
                'periodType': periodtype,
                'periodNum': periodnum,
                'id': vm_id
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/renewCloud', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_upgrade_order_price(self, cpu, memory, vm_id):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, cpu, memory, vm_id),
                'cpu': cpu,
                'memory': memory,
                'id': vm_id
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/getUpgradeOrderPrice', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def upgrade_cloud(self, cpu, memory, vm_id):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, cpu, memory, vm_id),
                'cpu': cpu,
                'memory': memory,
                'id': vm_id
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/upgradeCloud', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_data_disk_price(self, datahd=10, periodnum=1, zoneid=1):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, datahd, periodnum, zoneid),
                'datahd': datahd,
                'periodNum': periodnum,
                'zoneId': zoneid
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/getDatadiskPrice', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def buy_data_disk(self, datahd, periodnum=1, zoneid=1):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, datahd, periodnum, zoneid),
                'datahd': datahd,
                'periodNum': periodnum,
                'zoneId': zoneid
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/buyDatadisk', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_renew_data_disk_price(self, disk_id, periodnum):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, disk_id, periodnum),
                'diskId': disk_id,
                'periodNum': periodnum
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/getRenewDatadiskPrice', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def renew_data_disk(self, disk_id, periodnum):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, disk_id, periodnum),
                'diskId': disk_id,
                'periodNum': periodnum
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/renewDatadisk', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_upgrade_bandwidth_price(self, bw, zone_id, vm_id):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, bw, zone_id, vm_id),
                'bw': bw,
                'zoneId': zone_id,
                'id': vm_id
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/getUpgradeBandwidthPrice', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def upgrade_bandwidth(self, bw, zone_id, vm_id):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, bw, zone_id, vm_id),
                'bw': bw,
                'zoneId': zone_id,
                'id': vm_id
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/upgradeBandwidth', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def pay_order(self, order_id, cash):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, order_id, cash),
                'orderId': order_id,
                'cash': cash
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/payOrder', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def refund_cloud(self, vm_id, refund_detail):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id, refund_detail),
                'id': vm_id,
                'refundDetail': refund_detail
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/refundCloud', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def refund_disk(self, disk_id, refund_detail):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, disk_id, refund_detail),
                'diskId': disk_id,
                'refundDetail': refund_detail
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/refundDisk', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_order_list(self, page_no=1, page_size=2):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, page_no, page_size),
                'pageNo': page_no,
                'pageSize': page_size
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/getOrderList', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_order_detail(self, order_id):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, order_id),
                'orderId': order_id
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/getOrderDetail', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def cancel_order(self, order_id):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, order_id),
                'orderId': order_id
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/cancelOrder', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def buy_trial_cloud(self, cpu, memory, datahd, os, bw, zone_id):
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, cpu, memory, datahd, os, bw, zone_id),
                'cpu': cpu,
                'memory': memory,
                'datahd': datahd,
                'os': os,
                'bw': bw,
                'zoneId': zone_id
                }
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/buyTrialCloud', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_vm_list(self, page_no=1, page_size=2):
        # int:pageNo, page No.
        # int:pageSize, items of each page
        # int:uid, user id
        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, page_no, page_size),
                'pageNo': page_no,
                'pageSize': page_size}
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}

        result = self.connection.request('/api/getVMList', headers=headers, data=data, method='POST')
        # json_obj = json.loads(result.body)
        return json.loads(result.body)
    # return result.body

    def get_vm_list_by_orderid(self, order_id):
        # str:order_id
        # str:uid
        if not order_id:
            raise Exception('Invalid param order_id is empty')

        data = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, order_id),
                'orderId': order_id}
        data = urlencode(data)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getVMListByOrderId', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_vm_detail_info(self, vm_id):
        # str:id, vm id
        # str:uid, user id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id),
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getVMDetailInfo', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_vm_password(self, vm_id):
        # str:id, vm id
        # str:uid, user id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')
        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id),
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getVMPassword', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def reset_vm_password(self, vm_id):
        # str:id, vm id
        # str:uid, user id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id),
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/resetVMPassword', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_vm_status(self, vm_id):
        # str:id, vm id
        # str:uid, user id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id),
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getVMStatus', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def start_vm(self, vm_id):
        # str:id, vm id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id),
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/startVM', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def stop_vm(self, vm_id):
        # str:id, vm id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id),
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/stopVM', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def restart_vm(self, vm_id):
        # str:id, vm id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id),
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/restartVM', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_reinstall_os(self, vm_id):
        # str:id, vm id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id),
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getreinstallOS', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def reinstall_vm(self, vm_id, os_type=1):
        # str:id, vm id
        # int:os,
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id, os_type),
                'id': vm_id,
                'os': os_type}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/reinstallVM', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_data_disk_list(self, zone_id=1, page_no=1, page_size=1):
        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, page_no, page_size, zone_id),
                'pageNo': page_no,
                'pageSize': page_size,
                'zoneId': zone_id, }
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getDatadiskList', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_disk_list_by_orderid(self, order_id):
        # str:order_id, order id
        if not order_id:
            raise Exception('Invalid param order_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, order_id),
                'orderId': order_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getDiskListByOrderId', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_disk_list_by_vmid(self, vm_id):
        # str:id, vm id
        # str:uid, user id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id),
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getDiskListByVmId', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def rename_data_disk(self, disk_id, new_name='renameme', zone_id=1):
        # str:disk_id, disk id
        if not disk_id:
            raise Exception('Invalid param disk_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, disk_id, new_name, zone_id),
                'diskId': disk_id,
                'newName': new_name,
                'zoneId': zone_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/renameDatadisk', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def band_data_disk(self, disk_id, vm_id):
        # str:disk_id, disk id
        # str:id, vm id
        if not disk_id:
            raise Exception('Invalid param disk_id is empty')
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, disk_id, vm_id),
                'diskId': disk_id,
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/bandDatadisk', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def unband_data_disk(self, disk_id, vm_id):
        # str:disk_id, disk id
        # str:id, vm id
        if not disk_id:
            raise Exception('Invalid param disk_id is empty')
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, disk_id, vm_id),
                'diskId': disk_id,
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/unbandDatadisk', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_disk_status(self, disk_id):
        # str:disk_id, disk id
        # str:id, vm id
        if not disk_id:
            raise Exception('Invalid param disk_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, disk_id),
                'diskId': disk_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getDiskStatus', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_snapshot_list(self, zone_id=1, page_no=1, page_size=1):
        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, zone_id, page_no, page_size),
                'pageNo': page_no,
                'pageSize': page_size,
                'zoneId': zone_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/snapshotList', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def create_snapshot(self, vm_id, snapshot_name='renameme'):
        # str:id, vm id
        if not vm_id:
            raise Exception('Invalid param vm_id is empty')
        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id, snapshot_name),
                'snapshotName': snapshot_name,
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/createSnapshot', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_vm_snapshot_status(self, snapshot_id, zone_id=1):
        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, snapshot_id, zone_id),
                'snapshotId': snapshot_id,
                'zoneId': zone_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/vmSnapshotStatus', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def remove_snapshot(self, vm_id, snapshot_id):
        if not vm_id:
            raise Exception('Invalid param: vm_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id, snapshot_id),
                'snapshotId': snapshot_id,
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/removeSnapshot', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def rollback_snapshot(self, zone_id, snapshot_id):
        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, snapshot_id, zone_id),
                'snapshotId': snapshot_id,
                'zoneId': zone_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/rollbackSnapshot', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def get_snapshots_by_vmid(self, vm_id, zone_id):
        if not vm_id:
            raise Exception('Invalid param: vm_id is empty')
        if not zone_id:
            raise Exception('Invalid param: zone_id is empty')

        request_body = {'accessKey': self.accesskey,
                'vKey': md5(self.accesskey, self.screctkey, vm_id, zone_id),
                'zoneId': zone_id,
                'id': vm_id}
        data = urlencode(request_body)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        result = self.connection.request('/api/getSnapshotsByVmId', headers=headers, data=data, method='POST')
        return json.loads(result.body)

    def _to_nodes(self, objects):
        return [self._to_node(el) for el in objects]

    def _to_node(self, element):
        """
        Conver the json data to a Node Object
        :param element: json element
        :return: a Node Object
        """
        instance_id = element['id']
        name = element['vmName']
        state = CTYUN_NODE_STATE[element['vmStatus']]
        public_ip = element['publicIP']
        public_ips = [public_ip] if public_ip else []
        private_ip = element['privateIP']
        private_ips = [private_ip] if private_ip else []
        extra = {
                'applyDate': element['applyDate'],
                'dueDate': element['dueDate'],
                'zoneId': element['zoneId'],
                }

        return Node(id=instance_id, name=name, state=state,
                public_ips=public_ips, private_ips=private_ips,
                driver=self.connection.driver, extra=extra)

    def _to_volume(self, element):
        """
        Convert the json data to a Storage Volume Object
        :param element: json element
        :return: a Volume Object
        """
        disk_id = element['id']
        name = element['diskName']
        state = CTYUN_VOLUME_STATE[element['diskStatus']]
        size = element['diskSize']
        extra = {
                'diskId': element['diskId'],
                'isSysVolume': element['isSysVolume'],
                'isPackaged': element['isPackaged'],
                'status': CTYUN_VOLUME_STATE[str(element['status'])],
                'applyDate': element['applyDate'],
                'dueDate': element['dueDate'],
                'vmName': element['vmName'],
                }

        return StorageVolume(id=disk_id, name=name, size=int(size),
                driver=self, state=state, extra=extra)
