package main

import (
	"context"
	"encoding/base64"
	"testing"

	"github.com/aws/aws-lambda-go/events"

	"github.com/qsweber/lunch-buddies/internal/server"
)

type fakeServer struct{ got server.Request }

func (f *fakeServer) Handle(_ context.Context, req server.Request) server.Response {
	f.got = req
	return server.Response{StatusCode: 201, Body: "done", Headers: map[string]string{"X": "y"}}
}

func TestHandlerDecodesBodyAndLowercasesHeaders(t *testing.T) {
	f := &fakeServer{}
	req := events.APIGatewayV2HTTPRequest{
		RawPath:         "/api/v0/poll",
		Headers:         map[string]string{"X-Slack-Signature": "v0=abc"},
		Body:            base64.StdEncoding.EncodeToString([]byte("payload=%7B%7D")),
		IsBase64Encoded: true,
	}
	req.RequestContext.HTTP.Method = "POST"

	resp, err := newHandler(f)(context.Background(), req)
	if err != nil || resp.StatusCode != 201 || resp.Body != "done" {
		t.Fatalf("resp = %+v, err = %v", resp, err)
	}
	if f.got.Body != "payload=%7B%7D" || f.got.Headers["x-slack-signature"] != "v0=abc" || f.got.Method != "POST" {
		t.Errorf("request = %+v", f.got)
	}
}
