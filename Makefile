# Each Lambda is cmd/<name>/main.go, built to a "bootstrap" binary and zipped to dist/<name>.zip
# (the CDK app packages the zips from there).
LAMBDAS := apigateway dynamostream worker

.PHONY: build test vet fmt-check $(addprefix build-,$(LAMBDAS))

build: $(addprefix build-,$(LAMBDAS))

$(addprefix build-,$(LAMBDAS)): build-%:
	mkdir -p dist/$*
	GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o dist/$*/bootstrap ./cmd/$*
	cd dist/$* && zip -q -j -FS ../$*.zip bootstrap

test:
	go test -race ./...

vet:
	go vet ./...

fmt-check:
	@UNFORMATTED=$$(gofmt -l $$(find . -name '*.go' -not -path './cdk/node_modules/*')); \
	if [ -n "$$UNFORMATTED" ]; then echo "Not gofmt-formatted:"; echo "$$UNFORMATTED"; exit 1; fi
