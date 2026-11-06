// Command apigateway is the HTTP API Lambda that Slack calls.
package main

import (
	"context"
	"encoding/base64"
	"log"
	"strings"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"

	"github.com/qsweber/lunch-buddies/internal/server"
)

type apiGatewayHandler func(ctx context.Context, request events.APIGatewayV2HTTPRequest) (events.APIGatewayV2HTTPResponse, error)

// newHandler adapts HTTP API (payload format 2.0) events to the server's Request/Response
// types. Header names are lowercased (HTTP API already does this; we normalise anyway since
// signature verification looks them up by lowercase name).
func newHandler(srv server.Server) apiGatewayHandler {
	return func(ctx context.Context, request events.APIGatewayV2HTTPRequest) (events.APIGatewayV2HTTPResponse, error) {
		body := request.Body
		if request.IsBase64Encoded {
			decoded, err := base64.StdEncoding.DecodeString(body)
			if err != nil {
				return events.APIGatewayV2HTTPResponse{StatusCode: 400, Body: `{"error":"invalid base64 body"}`}, nil
			}
			body = string(decoded)
		}

		headers := make(map[string]string, len(request.Headers))
		for k, v := range request.Headers {
			headers[strings.ToLower(k)] = v
		}

		resp := srv.Handle(ctx, server.Request{
			Method:      request.RequestContext.HTTP.Method,
			Path:        request.RawPath,
			Headers:     headers,
			QueryParams: request.QueryStringParameters,
			Body:        body,
		})

		return events.APIGatewayV2HTTPResponse{
			StatusCode: resp.StatusCode,
			Body:       resp.Body,
			Headers:    resp.Headers,
		}, nil
	}
}

func main() {
	serviceCtx, err := server.NewServiceContext(context.Background())
	if err != nil {
		log.Fatalf("Failed to initialize service context: %v", err)
	}
	lambda.Start(newHandler(server.New(serviceCtx)))
}
