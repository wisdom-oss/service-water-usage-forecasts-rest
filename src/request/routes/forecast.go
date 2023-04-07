package routes

import (
	"microservice/vars/globals"
	"net/http"
)

// l is an alias for shorter code
var l = globals.HttpLogger

func NewForecast(w http.ResponseWriter, r *http.Request) {
	l.Info().Msg("new forecast requested")
}
