import QtQuick
import Quickshell
import Quickshell.Io

Item {
    id: root
    property bool opened: false
    property double launchingUntil: 0
    property string pendingAction: ""
    readonly property string launcher: decodeURIComponent(Qt.resolvedUrl("scripts/voice.py").toString().replace(/^file:\/\//, ""))

    function open(payloadJson) {
        launchingUntil = Date.now() + 15000
        opened = true
        control("--open")
    }
    function close() {
        launchingUntil = 0
        opened = false
        control("--close")
    }
    function control(action) {
        if (controller.running) {
            pendingAction = action
        } else {
            controller.command = ["python3", launcher, action]
            controller.running = true
        }
    }
    Process {
        id: controller
        onExited: {
            if (root.pendingAction !== "") {
                const action = root.pendingAction
                root.pendingAction = ""
                root.control(action)
            }
        }
    }
    Timer {
        interval: 1000
        running: true
        repeat: true
        onTriggered: if (!status.running) status.running = true
    }
    Process {
        id: status
        command: ["python3", root.launcher, "--status"]
        stdout: StdioCollector {
            onStreamFinished: {
                if (text.trim() === "open") {
                    root.launchingUntil = 0
                    root.opened = true
                } else if (Date.now() > root.launchingUntil) {
                    root.opened = false
                }
            }
        }
    }
}
