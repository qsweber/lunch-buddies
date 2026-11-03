package tokencipher

import (
	"context"
	"errors"
	"testing"

	"github.com/aws/aws-sdk-go-v2/service/kms"
)

// fakeKMS "encrypts" by prefixing the team id, and refuses to decrypt under a different
// encryption context, like real KMS.
type fakeKMS struct{ decrypts int }

func (f *fakeKMS) Encrypt(_ context.Context, p *kms.EncryptInput, _ ...func(*kms.Options)) (*kms.EncryptOutput, error) {
	return &kms.EncryptOutput{CiphertextBlob: append([]byte(p.EncryptionContext["team_id"]+":"), p.Plaintext...)}, nil
}

func (f *fakeKMS) Decrypt(_ context.Context, p *kms.DecryptInput, _ ...func(*kms.Options)) (*kms.DecryptOutput, error) {
	f.decrypts++
	prefix := p.EncryptionContext["team_id"] + ":"
	if len(p.CiphertextBlob) < len(prefix) || string(p.CiphertextBlob[:len(prefix)]) != prefix {
		return nil, errors.New("InvalidCiphertextException")
	}
	return &kms.DecryptOutput{Plaintext: p.CiphertextBlob[len(prefix):]}, nil
}

func TestKMSRoundTripCachesAndBindsTeam(t *testing.T) {
	f := &fakeKMS{}
	c := NewKMS(f, "alias/test")
	ct, err := c.Encrypt(context.Background(), "T1", "xoxb-secret")
	if err != nil {
		t.Fatal(err)
	}
	if ct == "xoxb-secret" {
		t.Fatal("ciphertext equals plaintext")
	}
	for range 3 {
		pt, err := c.Decrypt(context.Background(), "T1", ct)
		if err != nil || pt != "xoxb-secret" {
			t.Fatalf("Decrypt = %q, %v", pt, err)
		}
	}
	if f.decrypts != 1 {
		t.Errorf("decrypts = %d, want 1 (cached)", f.decrypts)
	}
	if _, err := NewKMS(f, "k").Decrypt(context.Background(), "T2", ct); err == nil {
		t.Error("decrypting under another team's context should fail")
	}
}
