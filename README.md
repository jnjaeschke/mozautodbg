# mozautodbg

## What is this?

The Mozilla build system `mach` allows to set so-called "build hooks".
These hooks allow to mix opt- and non-opt builds by removing the OPTIMIZE flag per directory,
which makes debug builds much more performant and usable.

This tool uses git information to determine which subdirectories have changes w.r.t. the merge base,
and sets those directories to nonopt.

## Installation

This is a Python tool. Therefore, installation uses Python mechanisms such as pip.

Either install it using

```sh
pip install git+https://github.com/jnjaeschke/mozautodbg
```

Or use developer mode:

```sh
git clone https://github.com/jnjaeschke/mozautodbg
cd mozautodbg
pip install -e .
```

## Configuration

`mozautodbg` needs to be configured before the first run. It currently expects to know about the mozconfig that should be used.
`mozautodbg configure` starts an interactive configuration assistant.
The assistent allows to set the default mozconfig, the default branch (typically `bookmarks/central`),
and default include and ignore lists.

## Usage

This tool is designed to be a drop-in replacement for `./mach`:

```sh
cd ~/gecko
mozautodbg mach build
mozautodbg mach run
mozautodbg mach wpt --headless --debugger=rr /foo
```

It is possible to override configuration settings:

```sh
mozautodbg mach --mozconfig=/home/user/some_other_mozconfig build
mozautodbg mach --include dom/base --ignore dom/bindings build
```

It's also possible to set a different base commit or branch:

```sh
mozautodbg mach --base <sha> build
```

### Example mozconfig

This is an (opinionated) example mozconfig:

```sh
mk_add_options MOZ_OBJDIR=@TOPSRCDIR@/obj-ff-dbg
mk_add_options 'export BUILDCACHE_DIR=/home/<user>/.buildcache_debug'
mk_add_options 'export RUSTC_WRAPPER=buildcache'
ac_add_options --with-ccache=buildcache
ac_add_options --enable-debug
ac_add_options --enable-linker=mold
mk_add_options AUTOCLOBBER=1
```

