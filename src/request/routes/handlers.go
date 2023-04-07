// Package routes
// This package contains all route handlers for the microservice
package routes

import (
	log "github.com/sirupsen/logrus"
	"io"
	requestErrors "microservice/request/error"
	"microservice/vars/globals"
	"net/http"
	"os"
)

/*
BasicHandler

This handler shows how a basic handler works and how to send back a message
*/
func BasicHandler(responseWriter http.ResponseWriter, request *http.Request) {
	_, err := responseWriter.Write([]byte("Hello World"))
	if err != nil {
		log.WithError(err).Error("Unable to send response to the client")
	}
}

func GatewayConfig(responseWriter http.ResponseWriter, request *http.Request) {
	configFile, err := os.Open(globals.Environment["GATEWAY_CONFIG_LOCATION"])
	if err != nil {
		e, _ := requestErrors.WrapInternalError(err)
		requestErrors.SendError(e, responseWriter)
		return
	}

	configFileContents, readErr := io.ReadAll(configFile)
	if readErr != nil {
		e, _ := requestErrors.WrapInternalError(err)
		requestErrors.SendError(e, responseWriter)
		return
	}

	responseWriter.Header().Set("Content-Type", "text/json")
	responseWriter.WriteHeader(200)
	responseWriter.Write(configFileContents)
}
