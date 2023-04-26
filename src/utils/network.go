package wisdomUtils

import (
	"fmt"
	"net"
	"time"
)

// PingHost tries to ping the supplied host on the supplied port by dialing to it via tcp.
// If the dial was successful in the specified timeout, the function will return true.
//
// Parameters:
//   - host: the host which shall be pinged
//   - port: the port which shall be pinged on the host
//   - timeout: the timeout which is set for the ping in seconds
func PingHost(host string, port string, timeout int) bool {
	connectionTimeout := time.Duration(timeout) * time.Second
	connectionTarget := fmt.Sprintf("%s:%s", host, port)
	connection, connectionError := net.DialTimeout("tcp", connectionTarget, connectionTimeout)
	if connectionError != nil {
		return false
	} else {
		_ = connection.Close()
		return true
	}
}
