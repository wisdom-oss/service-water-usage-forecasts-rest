package routes

import (
	"microservice/utils"
	"microservice/vars"
	"net/http"
)

// HealthCheck handles requests to the healthcheck endpoint. The endpoint is used by docker and the
// api gateway to check for the service availability
func HealthCheck(w http.ResponseWriter, _ *http.Request) {
	// check if the postgres database is reachable
	pingError := vars.PostgresConnection.Ping()
	if pingError != nil {
		w.WriteHeader(http.StatusInternalServerError)
		return
	}

	// check if the api gateway is reachable
	gatewayReachable := utils.PingHost(vars.APIGatewayHost, vars.APIGatewayPort, 5)
	if !gatewayReachable {
		w.WriteHeader(http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusNoContent)
	return
}
