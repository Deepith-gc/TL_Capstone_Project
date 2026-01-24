from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel


class SimpleTopo(Topo):
    def build(self):

        h1 = self.addHost('h1')
        h2 = self.addHost('h2')
        h3 = self.addHost('h3')
        h4 = self.addHost('h4')

        s1 = self.addSwitch('s1', protocols='OpenFlow13')
        s2 = self.addSwitch('s2', protocols='OpenFlow13')
        s3 = self.addSwitch('s3', protocols='OpenFlow13')

        self.addLink(h1, s1)
        self.addLink(h2, s1)

        self.addLink(s1, s2)
        self.addLink(s1, s3)

        self.addLink(s2, h3)
        self.addLink(s3, h4)


def run():
    topo = SimpleTopo()

    net = Mininet(
        topo=topo,
        controller=RemoteController('ryu', ip='127.0.0.1', port=6653),
        switch=OVSSwitch,
        autoSetMacs=True,
        autoStaticArp=True
    )

    net.start()
    print("[INFO] Network started")

    CLI(net)
    net.stop()


if __name__ == '__main__':
    setLogLevel('info')
    run()
