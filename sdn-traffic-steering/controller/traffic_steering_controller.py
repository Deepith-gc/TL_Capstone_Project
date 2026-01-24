from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ipv4, tcp, udp
from ryu.app.wsgi import ControllerBase, WSGIApplication, route
from webob import Response
import json

APP_NAME = 'traffic_steering'


class TrafficSteeringSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.mac_to_port = {}

        # Traffic steering policy (src_ip, dst_ip) -> out_port
        self.steering_policy = {
            ("10.0.0.1", "10.0.0.3"): 2,
            ("10.0.0.2", "10.0.0.3"): 3,
            ("10.0.0.1", "10.0.0.4"): 3,
            ("10.0.0.2", "10.0.0.4"): 2
        }

        self.logger.info("Traffic Steering Controller Started")

        # WSGI for REST API
        wsgi = kwargs['wsgi']
        wsgi.register(SteeringAPI, {APP_NAME: self})

    # Table-miss flow
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser

        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=0, match=match, instructions=inst)
        dp.send_msg(mod)
        self.logger.info(f"Switch {dp.id} connected")

    # Packet-in handler
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth.ethertype == 0x88cc:  # Ignore LLDP
            return

        src = eth.src
        dst = eth.dst

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][src] = in_port

        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        udp_pkt = pkt.get_protocol(udp.udp)

        steering_key = None
        if ip_pkt and (tcp_pkt or udp_pkt):
            steering_key = (ip_pkt.src, ip_pkt.dst)

        if steering_key in self.steering_policy:
            out_port = self.steering_policy[steering_key]
        else:
            out_port = self.mac_to_port[dpid].get(dst, ofp.OFPP_FLOOD)

        actions = [parser.OFPActionOutput(out_port)]

        if out_port != ofp.OFPP_FLOOD:
            match = parser.OFPMatch(
                eth_type=0x0800,
                ipv4_src=ip_pkt.src,
                ipv4_dst=ip_pkt.dst
            ) if ip_pkt else parser.OFPMatch(eth_src=src, eth_dst=dst)

            inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(datapath=dp, priority=10, match=match, instructions=inst)
            dp.send_msg(mod)

        out = parser.OFPPacketOut(
            datapath=dp,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data
        )
        dp.send_msg(out)


# REST API class
class SteeringAPI(ControllerBase):
    def __init__(self, req, link, data, **config):
        super().__init__(req, link, data, **config)
        self.app = data[APP_NAME]

    # Add CORS headers
    def _set_cors(self, resp):
        resp.headers['Access-Control-Allow-Origin'] = '*'
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'

    # Handle OPTIONS preflight requests
    @route('traffic_steering', '/steer', methods=['OPTIONS'])
    def options_steer(self, req, **kwargs):
        resp = Response()
        self._set_cors(resp)
        return resp

    @route('traffic_steering', '/ports', methods=['GET'])
    def get_ports(self, req, **kwargs):
        dst_ip = req.GET.get('dst')
        ports = [port for (src, dst), port in self.app.steering_policy.items() if dst == dst_ip]
        resp = Response(content_type='application/json', body=json.dumps({'ports': ports}).encode('utf-8'))
        self._set_cors(resp)
        return resp

    @route('traffic_steering', '/steer', methods=['POST'])
    def steer_traffic(self, req, **kwargs):
        try:
            data = req.json if req.body else {}
            src_ip = data.get('src_ip')
            dst_ip = data.get('dst_ip')
            out_port = data.get('out_port')
            if src_ip and dst_ip and out_port:
                self.app.steering_policy[(src_ip, dst_ip)] = int(out_port)

            resp = Response(content_type='application/json', body=json.dumps({'status': 'ok'}).encode('utf-8'))
            self._set_cors(resp)
            return resp
        except Exception as e:
            resp = Response(
                content_type='application/json',
                body=json.dumps({'status': 'error', 'msg': str(e)}).encode('utf-8')
            )
            self._set_cors(resp)
            return resp
