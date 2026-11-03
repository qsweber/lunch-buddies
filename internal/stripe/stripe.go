// Package stripe is a minimal Stripe REST client for customer and invoice calls. When no API
// key is configured every call is a no-op, matching the Python client.
package stripe

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

type Customer struct{ ID string }

type Invoice struct {
	ID        string
	CreatedAt time.Time
}

type LineItem struct {
	// AmountCents is in the smallest currency unit, as the Stripe API expects.
	AmountCents int64
	Description string
}

type API interface {
	// CreateCustomer returns nil when Stripe isn't configured.
	CreateCustomer(ctx context.Context, name, email, teamName string) (*Customer, error)
	UpdateCustomer(ctx context.Context, customerID, name, email, teamName string) error
	// LatestInvoice returns nil if the customer has no invoices or Stripe isn't configured.
	LatestInvoice(ctx context.Context, customerID string) (*Invoice, error)
	// CreateInvoice returns nil when Stripe isn't configured.
	CreateInvoice(ctx context.Context, customerID string, items []LineItem) (*Invoice, error)
}

type Client struct {
	APIKey     string
	BaseURL    string
	HTTPClient *http.Client
	Now        func() time.Time
}

func New(apiKey string) *Client {
	return &Client{APIKey: apiKey, BaseURL: "https://api.stripe.com/v1/", HTTPClient: &http.Client{Timeout: 15 * time.Second}, Now: time.Now}
}

func (c *Client) do(ctx context.Context, method, path string, form url.Values, out any) error {
	var body io.Reader
	target := c.BaseURL + path
	if method == http.MethodGet {
		target += "?" + form.Encode()
	} else {
		body = strings.NewReader(form.Encode())
	}
	req, err := http.NewRequestWithContext(ctx, method, target, body)
	if err != nil {
		return err
	}
	req.SetBasicAuth(c.APIKey, "")
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}
	if resp.StatusCode >= 300 {
		return fmt.Errorf("stripe %s %s: HTTP %d: %s", method, path, resp.StatusCode, raw)
	}
	if out != nil {
		return json.Unmarshal(raw, out)
	}
	return nil
}

func (c *Client) CreateCustomer(ctx context.Context, name, email, teamName string) (*Customer, error) {
	if c.APIKey == "" {
		return nil, nil
	}
	var out struct {
		ID string `json:"id"`
	}
	err := c.do(ctx, http.MethodPost, "customers", url.Values{"name": {name}, "email": {email}, "description": {teamName}}, &out)
	if err != nil {
		return nil, err
	}
	return &Customer{ID: out.ID}, nil
}

func (c *Client) UpdateCustomer(ctx context.Context, customerID, name, email, teamName string) error {
	if c.APIKey == "" {
		return nil
	}
	return c.do(ctx, http.MethodPost, "customers/"+url.PathEscape(customerID), url.Values{"name": {name}, "email": {email}, "description": {teamName}}, nil)
}

type invoiceJSON struct {
	ID      string `json:"id"`
	Created int64  `json:"created"`
}

func (c *Client) LatestInvoice(ctx context.Context, customerID string) (*Invoice, error) {
	if c.APIKey == "" {
		return nil, nil
	}
	var out struct {
		Data []invoiceJSON `json:"data"`
	}
	if err := c.do(ctx, http.MethodGet, "invoices", url.Values{"customer": {customerID}, "limit": {"1"}}, &out); err != nil {
		return nil, err
	}
	if len(out.Data) == 0 {
		return nil, nil
	}
	return &Invoice{ID: out.Data[0].ID, CreatedAt: time.Unix(out.Data[0].Created, 0)}, nil
}

func (c *Client) CreateInvoice(ctx context.Context, customerID string, items []LineItem) (*Invoice, error) {
	if c.APIKey == "" {
		return nil, nil
	}
	for _, item := range items {
		err := c.do(ctx, http.MethodPost, "invoiceitems", url.Values{
			"customer":    {customerID},
			"amount":      {strconv.FormatInt(item.AmountCents, 10)},
			"currency":    {"usd"},
			"description": {item.Description},
		}, nil)
		if err != nil {
			return nil, err
		}
	}
	var out invoiceJSON
	err := c.do(ctx, http.MethodPost, "invoices", url.Values{
		"customer":          {customerID},
		"auto_advance":      {"true"},
		"collection_method": {"send_invoice"},
		"due_date":          {strconv.FormatInt(c.Now().Add(30*24*time.Hour).Unix(), 10)},
		"description":       {"memo"},
	}, &out)
	if err != nil {
		return nil, err
	}
	return &Invoice{ID: out.ID, CreatedAt: time.Unix(out.Created, 0)}, nil
}

var _ API = (*Client)(nil)
