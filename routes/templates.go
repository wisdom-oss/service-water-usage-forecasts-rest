package routes

import (
	"errors"
	"net/http"
)

// BasicHandler contains just a response, that is used to show the templating
func BasicHandler(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("hello there"))
}

func BasicWithInternalErrorHandling(w http.ResponseWriter, r *http.Request) {
	// access the error handlers
	nativeErrorChannel := r.Context().Value("nativeErrorChannel").(chan error)
	nativeErrorHandled := r.Context().Value("nativeErrorHandled").(chan bool)
	// now publish an error to each of the wisdom errors
	nativeErrorChannel <- errors.New("native test error")
	// now block until the error has been handled
	<-nativeErrorHandled
	return
}

func BasicWithWISdoMErrorHandling(w http.ResponseWriter, r *http.Request) {
	// access the error handlers
	wisdomErrorChannel := r.Context().Value("wisdomErrorChannel").(chan string)
	wisdomErrorHandled := r.Context().Value("wisdomErrorHandled").(chan bool)
	// now publish an error to each of the wisdom errors
	wisdomErrorChannel <- "TEMPLATE"
	<-wisdomErrorHandled
	return
}
