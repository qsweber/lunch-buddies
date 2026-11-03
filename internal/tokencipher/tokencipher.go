// Package tokencipher encrypts Slack bot tokens before they are written to DynamoDB, so the
// table (and its exports, backups and stream) only ever hold ciphertext. Each token is
// encrypted directly with a KMS key (tokens are far below KMS's 4 KB plaintext limit), bound
// to its team with an encryption context so a ciphertext can't be replayed onto another team.
package tokencipher

import (
	"context"
	"encoding/base64"
	"errors"
	"sync"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/kms"
)

// Cipher is what the repositories depend on.
type Cipher interface {
	Encrypt(ctx context.Context, teamID, plaintext string) (string, error)
	Decrypt(ctx context.Context, teamID, ciphertext string) (string, error)
}

// KMSAPI is the subset of the KMS client used here.
type KMSAPI interface {
	Encrypt(ctx context.Context, params *kms.EncryptInput, optFns ...func(*kms.Options)) (*kms.EncryptOutput, error)
	Decrypt(ctx context.Context, params *kms.DecryptInput, optFns ...func(*kms.Options)) (*kms.DecryptOutput, error)
}

const contextKey = "team_id"

// KMS encrypts with a KMS key and caches decrypted tokens for the life of the Lambda
// instance, so a warm instance decrypts each team's token once.
type KMS struct {
	client KMSAPI
	keyID  string

	mu    sync.Mutex
	cache map[string]string // ciphertext -> plaintext
}

func NewKMS(client KMSAPI, keyID string) *KMS {
	return &KMS{client: client, keyID: keyID, cache: map[string]string{}}
}

func (k *KMS) Encrypt(ctx context.Context, teamID, plaintext string) (string, error) {
	if k.keyID == "" {
		return "", errors.New("tokencipher: no KMS key configured")
	}
	out, err := k.client.Encrypt(ctx, &kms.EncryptInput{
		KeyId:             aws.String(k.keyID),
		Plaintext:         []byte(plaintext),
		EncryptionContext: map[string]string{contextKey: teamID},
	})
	if err != nil {
		return "", err
	}
	return base64.StdEncoding.EncodeToString(out.CiphertextBlob), nil
}

func (k *KMS) Decrypt(ctx context.Context, teamID, ciphertext string) (string, error) {
	k.mu.Lock()
	if v, ok := k.cache[ciphertext]; ok {
		k.mu.Unlock()
		return v, nil
	}
	k.mu.Unlock()

	blob, err := base64.StdEncoding.DecodeString(ciphertext)
	if err != nil {
		return "", err
	}
	out, err := k.client.Decrypt(ctx, &kms.DecryptInput{
		CiphertextBlob:    blob,
		EncryptionContext: map[string]string{contextKey: teamID},
	})
	if err != nil {
		return "", err
	}
	plaintext := string(out.Plaintext)

	k.mu.Lock()
	k.cache[ciphertext] = plaintext
	k.mu.Unlock()
	return plaintext, nil
}

// Plaintext is a no-op cipher for local development and tests. Never use it in a deployed
// stack.
type Plaintext struct{}

func (Plaintext) Encrypt(_ context.Context, _, p string) (string, error) { return p, nil }
func (Plaintext) Decrypt(_ context.Context, _, c string) (string, error) { return c, nil }
