package policy_test

import (
	"github.com/google/cel-go/cel"
	"gopkg.in/yaml.v3"
	"os"
	"testing"
)

func TestAllowlistExpressions(t *testing.T) {
	data, err := os.ReadFile("../allowed-registries.yaml")
	if err != nil {
		t.Fatal(err)
	}
	var policy struct {
		Spec struct {
			Variables []struct {
				Name       string
				Expression string
			}
			Validations []struct{ Expression string }
		}
	}
	if err := yaml.Unmarshal(data, &policy); err != nil {
		t.Fatal(err)
	}
	env, err := cel.NewEnv(cel.Variable("object", cel.DynType), cel.Variable("variables", cel.DynType))
	if err != nil {
		t.Fatal(err)
	}
	eval := func(expression string, object, variables map[string]any) any {
		ast, issues := env.Compile(expression)
		if issues.Err() != nil {
			t.Fatal(issues.Err())
		}
		program, err := env.Program(ast)
		if err != nil {
			t.Fatal(err)
		}
		result, _, err := program.Eval(map[string]any{"object": object, "variables": variables})
		if err != nil {
			t.Fatal(err)
		}
		return result.Value()
	}
	image := func(reference string) []any { return []any{map[string]any{"name": "test", "image": reference}} }
	for _, tc := range []struct {
		name, main, init, debug string
		allowed                 bool
	}{
		{"demo", "ghcr.io/open-telemetry/demo:3.1.0-quote", "", "", true},
		{"collector", "docker.io/otel/opentelemetry-collector-contrib:0.160.0", "", "", true},
		{"digest", "docker.io/library/busybox@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "", "", true},
		{"unapproved host", "unapproved.example/team/app:1", "", "", false},
		{"lookalike host", "ghcr.io.evil.example/open-telemetry/demo:1", "", "", false},
		{"wrong project", "ghcr.io/other-project/demo:1", "", "", false},
		{"lookalike project", "ghcr.io/open-telemetry-evil/demo:1", "", "", false},
		{"short name", "busybox:1.37.0", "", "", false},
		{"implicit docker host", "otel/opentelemetry-collector-contrib:0.160.0", "", "", false},
		{"unapproved port", "docker.io:5000/library/busybox:1", "", "", false},
		{"approved init", "docker.io/library/busybox:1", "docker.io/library/busybox:1", "", true},
		{"denied init", "docker.io/library/busybox:1", "evil.example/init:1", "", false},
		{"approved debug", "docker.io/library/busybox:1", "", "docker.io/library/busybox:1", true},
		{"denied debug", "docker.io/library/busybox:1", "", "evil.example/debug:1", false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			spec := map[string]any{"containers": image(tc.main)}
			if tc.init != "" {
				spec["initContainers"] = image(tc.init)
			}
			if tc.debug != "" {
				spec["ephemeralContainers"] = image(tc.debug)
			}
			object := map[string]any{"spec": spec}
			variables := map[string]any{}
			for _, variable := range policy.Spec.Variables {
				variables[variable.Name] = eval(variable.Expression, object, variables)
			}
			if len(policy.Spec.Validations) != 1 {
				t.Fatal("expected one validation")
			}
			result := eval(policy.Spec.Validations[0].Expression, object, variables)
			if result != tc.allowed {
				t.Fatalf("got %v; expected allowed=%v", result, tc.allowed)
			}
		})
	}
}
