"""Helpers shared by the package build configuration and its tests."""


def get_linux_attach_binary(plat_name: str | None) -> str | None:
    """Return the Linux attach binary for a wheel platform name.

    ``plat_name`` is the target platform embedded in a wheel name. It can
    differ from the platform running the build, for example when a package is
    cross-built. Unknown platforms intentionally return no binary instead of
    guessing which architecture is compatible.
    """

    if not plat_name:
        return None

    normalized = plat_name.lower().replace("-", "_").replace(".", "_")
    if not normalized.startswith(("linux_", "manylinux", "musllinux")):
        return None

    if normalized.endswith(("x86_64", "amd64")):
        return "attach_process/attach_linux_amd64.so"
    if normalized.endswith(("i686", "i386", "x86")):
        return "attach_process/attach_linux_x86.so"
    return None
