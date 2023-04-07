package wisdomMiddleware

import (
	"encoding/json"
	"github.com/rs/zerolog/log"
	"github.com/titanous/json5"
	"net/http"
	"os"
)

// GatewayConfigInterceptor allows the microservice to deliver the gateway configuration file to the microservice polling the
// docker host. This middleware should be used before any authorization middleware since the watcher will not authenticate itself
func GatewayConfigInterceptor(gatewayConfigFile string, queryPath string) func(handler http.Handler) http.Handler {
	logger := log.With().
		Str("wisdomMiddleware", "GatewayConfigInterceptor").
		Str("queryPath", queryPath).
		Str("filePath", gatewayConfigFile).
		Logger()

	return func(nextHandler http.Handler) http.Handler {
		return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
			if r.URL.Path != queryPath {
				nextHandler.ServeHTTP(w, r)
				return
			}
			// since the query path was matched to the one supplied to the handler start the process of sending
			// the data
			logger.Info().Msg("intercepted request for gateway configuration")
			logger.Debug().Str("filePath", gatewayConfigFile).Msg("loading configuration")
			// try to open the file path supplied
			configFile, err := os.Open(gatewayConfigFile)
			if err != nil {
				logger.Error().Err(err).Msg("unable to open configuration file")
				w.WriteHeader(500)
				return
			}
			logger.Debug().Msg("opened configuration file")
			// now use the json5 package to read the file
			var config interface{}
			err = json5.NewDecoder(configFile).Decode(&config)
			if err != nil {
				logger.Error().Err(err).Msg("unable to parse configuration file")
				w.WriteHeader(500)
				return
			}
			// now use the json package to write out the read interface
			w.Header().Set("Content-Type", "text/json")
			err = json.NewEncoder(w).Encode(config)
			if err != nil {
				w.WriteHeader(500)
				logger.Error().Err(err).Msg("unable to send configuration file")
				return
			}
			logger.Info().Msg("delivered gateway configuration")
		})
	}
}
