package clipboard

import (
	"context"
	"errors"
	"testing"
)

func TestExplicitNativeOverrideWinsOverHeadlessDetection(t *testing.T) {
	deps := testDeps(map[string]string{"PROMPTCRAFT_CLIPBOARD": "native"})
	if !Headless(deps) {
		t.Fatal("the fixture must be headless for this test to mean anything")
	}

	nativeCalled := false
	deps.NativeCopy = func(text string) error {
		nativeCalled = true
		return nil
	}
	deps.OSC52Writer = func(text string) error { return errors.New("must not be used") }

	if route := Copy("prompt", deps); route != RouteNative {
		t.Fatalf("an explicit native mode must be honoured: got %q", route)
	}
	if !nativeCalled {
		t.Fatal("the native backend must have been used")
	}
}

func TestWaylandSessionIsNotHeadless(t *testing.T) {
	deps := testDeps(map[string]string{"WAYLAND_DISPLAY": "wayland-0"})
	if Headless(deps) {
		t.Fatal("a Wayland session has a native clipboard even without X11")
	}

	deps.NativeCopy = func(text string) error { return nil }
	deps.OSC52Writer = func(text string) error { return errors.New("must not be used") }
	if route := Copy("prompt", deps); route != RouteNative {
		t.Fatalf("expected the native route on Wayland, got %q", route)
	}
}

func TestCancellableBackendIsPreferred(t *testing.T) {
	deps := testDeps(map[string]string{"DISPLAY": ":0", "X11_SOCKET": "yes"})

	used := false
	deps.NativeCopyWithContext = func(ctx context.Context, text string) error {
		used = true
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
			return nil
		}
	}

	if route := Copy("prompt", deps); route != RouteNative || !used {
		t.Fatalf("the cancellable backend must be preferred: %q / %v", route, used)
	}

	// A cancellable backend reports the timeout through its context.
	deps.NativeCopyWithContext = func(ctx context.Context, text string) error {
		<-ctx.Done()
		return ctx.Err()
	}
	deps.OSC52Writer = func(text string) error { return errors.New("writer unavailable") }
	if route := Copy("prompt", deps); route != "" {
		t.Fatalf("a cancelled copy must not report a route, got %q", route)
	}
}
