const CTRL = "http://192.168.56.105:8080";

document.getElementById("dst_ip").addEventListener("change", loadPorts);

function loadPorts() {
    const dst_ip = document.getElementById("dst_ip").value;
    const out_port_select = document.getElementById("out_port");
    out_port_select.innerHTML = '<option value="">-- Select Path --</option>';

    if (!dst_ip) return;

    fetch(`${CTRL}/ports?dst=${dst_ip}`)
        .then(resp => resp.json())
        .then(data => {
            data.ports.forEach(port => {
                const opt = document.createElement("option");
                opt.value = port;
                opt.innerText = "Port " + port;
                out_port_select.appendChild(opt);
            });
        })
        .catch(err => {
            document.getElementById("status").innerText = "Controller not reachable";
        });
}

function steerTraffic() {
    const src_ip = document.getElementById("src_ip").value;
    const dst_ip = document.getElementById("dst_ip").value;
    const out_port = document.getElementById("out_port").value;

    if (!src_ip || !dst_ip || !out_port) {
        document.getElementById("status").innerText = "Fill all fields";
        return;
    }

    fetch(`${CTRL}/steer`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ src_ip, dst_ip, out_port: parseInt(out_port) })
    })
    .then(resp => resp.json())
    .then(data => {
        document.getElementById("status").innerText = "Traffic steered successfully";
    })
    .catch(err => {
        document.getElementById("status").innerText = "Controller not reachable";
    });
}

