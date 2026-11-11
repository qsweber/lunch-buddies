package params

import (
	"context"
	"strings"
	"testing"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/ssm"
	"github.com/aws/aws-sdk-go-v2/service/ssm/types"
)

type fakeSSM struct {
	pages  [][]types.Parameter
	inputs []ssm.GetParametersByPathInput
}

func (f *fakeSSM) GetParametersByPath(_ context.Context, p *ssm.GetParametersByPathInput, _ ...func(*ssm.Options)) (*ssm.GetParametersByPathOutput, error) {
	f.inputs = append(f.inputs, *p)
	i := len(f.inputs) - 1
	out := &ssm.GetParametersByPathOutput{Parameters: f.pages[i]}
	if i < len(f.pages)-1 {
		out.NextToken = aws.String("next")
	}
	return out, nil
}

func param(name, value string) types.Parameter {
	return types.Parameter{Name: aws.String(name), Value: aws.String(value)}
}

func TestLoadPaginatesDecryptsAndStripsPrefix(t *testing.T) {
	f := &fakeSSM{pages: [][]types.Parameter{
		{param("/lunch-buddies/dev/a", "1")},
		{param("/lunch-buddies/dev/b", "2")},
	}}
	got, err := Load(context.Background(), f, "/lunch-buddies/dev/", []string{"a", "b"})
	if err != nil {
		t.Fatal(err)
	}
	if got["a"] != "1" || got["b"] != "2" {
		t.Errorf("values = %v", got)
	}
	if len(f.inputs) != 2 || aws.ToString(f.inputs[0].Path) != "/lunch-buddies/dev" || !aws.ToBool(f.inputs[0].WithDecryption) {
		t.Errorf("inputs = %+v", f.inputs)
	}
}

func TestLoadReportsEveryMissingKey(t *testing.T) {
	f := &fakeSSM{pages: [][]types.Parameter{{param("/p/a", "1"), param("/p/b", "")}}}
	_, err := Load(context.Background(), f, "/p", []string{"a", "b", "c"})
	if err == nil || !strings.Contains(err.Error(), "/p/b, /p/c") {
		t.Errorf("err = %v", err)
	}
}
