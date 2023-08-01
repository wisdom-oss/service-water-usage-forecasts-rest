package main

import (
	"fmt"
	"github.com/go-chi/chi/v5"
	chiMiddleware "github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/httplog"
	"github.com/rs/zerolog/log"
	wisdomMiddleware "github.com/wisdom-oss/microservice-middlewares/v2"
	"microservice/routes"
	"net/http"
	"os"
	"os/signal"
	"time"

	"microservice/globals"
)

// the main function bootstraps the http server and handlers used for this
// microservice
func main() {
	// create a new logger for the main function
	l := log.With().Str("step", "main-service").Logger()
	l.Info().Msgf("starting %s service", globals.ServiceName)

	// create a new router
	router := chi.NewRouter()
	// add some middlewares to the router to allow identifying requests
	router.Use(wisdomMiddleware.NativeErrorHandler(globals.ServiceName))
	router.Use(wisdomMiddleware.WISdoMErrorHandler(globals.Errors))
	router.Use(chiMiddleware.RequestID)
	router.Use(chiMiddleware.RealIP)
	router.Use(httplog.Handler(l))
	// now add the authorization middleware to the router
	router.Use(wisdomMiddleware.Authorization(globals.AuthorizationConfiguration, globals.ServiceName))
	// now mount the admin router
	router.HandleFunc("/{model}", routes.NewForecast)

	// now boot up the service
	// Configure the HTTP server
	server := &http.Server{
		Addr:         fmt.Sprintf("0.0.0.0:%s", globals.Environment["LISTEN_PORT"]),
		WriteTimeout: time.Second * 600,
		ReadTimeout:  time.Second * 600,
		IdleTimeout:  time.Second * 600,
		Handler:      router,
	}

	// Start the server and log errors that happen while running it
	go func() {
		if err := server.ListenAndServe(); err != nil {
			l.Fatal().Err(err).Msg("An error occurred while starting the http server")
		}
	}()

	// Set up the signal handling to allow the server to shut down gracefully

	cancelSignal := make(chan os.Signal, 1)
	signal.Notify(cancelSignal, os.Interrupt)

	// Block further code execution until the shutdown signal was received
	<-cancelSignal

}
