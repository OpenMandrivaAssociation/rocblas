# HIP BLAS library (TheRock 7.14). Tensile GEMMs including gfx803 (r9nano).

Name:		rocblas
Version:	7.14.0
Release:	1
%{!?rocm_llvm_maj_ver:%global rocm_llvm_maj_ver 23}
Summary:	HIP Basic Linear Algebra Subprograms library
License:	BSD-3-Clause AND MIT
Group:		System/Libraries
URL:		https://github.com/ROCm/rocm-libraries
Source0:	https://github.com/ROCm/rocm-libraries/releases/download/therock-7.14/rocblas.tar.gz#/rocblas-%{version}.tar.gz
# Clang 23 freestanding headers: strncmp needs <cstring>
Patch0:		0001-include-cstring.patch
# Soft-fail missing Tensile library → source GEMM fallback
Patch1:		0002-soft-fail-missing-tensile-lib.patch

BuildRequires:	rocm-rpm-macros
BuildRequires:	cmake
BuildRequires:	ninja
BuildRequires:	rocm-cmake
BuildRequires:	hipcc
BuildRequires:	rocminfo
BuildRequires:	clang-tools
BuildRequires:	rocm-hip-devel
BuildRequires:	clang >= %{rocm_llvm_maj_ver}
BuildRequires:	llvm-devel >= %{rocm_llvm_maj_ver}
BuildRequires:	python3
BuildRequires:	python-tensile
BuildRequires:	python%{pyver}dist(pyyaml)
BuildRequires:	python%{pyver}dist(msgpack)
BuildRequires:	python%{pyver}dist(joblib)
BuildRequires:	python%{pyver}dist(rich)
BuildRequires:	pkgconfig(msgpack-c)
BuildRequires:	lib64msgpack-c-devel
BuildRequires:	lib64msgpack-cpp-devel
# GTest not needed with clients off

ExclusiveArch:	%{x86_64} %{aarch64}

%description
rocBLAS provides BLAS Level 1/2/3 for HIP. Dense GEMM kernels are generated at
build time by Tensile from logic YAML (source-only). GPU targets from
%%rocm_gpu_targets_blas (includes gfx803 r9nano and GFX11/12 with true16 Tensile).

%package devel
Summary:	Development files for rocblas
Group:		Development/C++
Requires:	%{name}%{?_isa} = %{version}-%{release}
Requires:	rocm-hip-devel
Provides:	rocblas-devel = %{EVRD}

%description devel
Headers and CMake package for rocblas.

%prep
%autosetup -n rocblas -p1

export CXX=hipcc
export CC=clang
export ROCM_PATH=%{_prefix}
export HIP_PATH=%{_prefix}
CXXFLAGS=$(printf '%s' "%{optflags}" | sed -E 's/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')
export CXXFLAGS
export CFLAGS="$CXXFLAGS"
export LDFLAGS=$(printf '%s' "%{?__global_ldflags}" | sed -E 's/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')
# Point Tensile at the system package root
TENSILE_ROOT=$(python3 -c 'import Tensile, os; print(os.path.dirname(Tensile.__file__))')
export TENSILE_ROOT
# Tensile multi-arch: Tensile_CPU_THREADS=8 (32 OOMs on ~64G). Prefer TMPDIR on large disk.
%cmake %{rocm_cmake_fhs} %{rocm_cmake_gpu_targets_blas} \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_CXX_COMPILER=hipcc \
	-DCMAKE_CXX_FLAGS="$CXXFLAGS" \
	-DBUILD_SHARED_LIBS=ON \
	-DBUILD_WITH_TENSILE=ON \
	-DBUILD_WITH_HIPBLASLT=OFF \
	-DBUILD_WITH_PIP=OFF \
	-DBUILD_CLIENTS_TESTS=OFF \
	-DBUILD_CLIENTS_BENCHMARKS=OFF \
	-DBUILD_CLIENTS_SAMPLES=OFF \
	-DBUILD_FORTRAN_CLIENTS=OFF \
	-DTensile_ROOT="$TENSILE_ROOT" \
	-DTensile_LOGIC=asm_full \
	-DTensile_LIBRARY_FORMAT=msgpack \
	-DTensile_CODE_OBJECT_VERSION=default \
	-DTensile_CPU_THREADS=8 \
	-DROCM_PATH=%{_prefix} \
	-DCMAKE_PREFIX_PATH=%{_prefix} \
	-G Ninja

%build
# Tensile toolchain expects ROCm-style amdclang / amdclang++ names
mkdir -p toolchain-bin
ln -sfn "$(command -v clang)" toolchain-bin/amdclang
ln -sfn "$(command -v clang++)" toolchain-bin/amdclang++
# Prefer hipcc for device code when named as amdclang++
ln -sfn "$(command -v hipcc)" toolchain-bin/hipcc
export PATH="%{_builddir}/rocblas/toolchain-bin:$PATH"
%ninja_build -C build

%install
%ninja_install -C build
if [ -d %{buildroot}/usr/lib/cmake/rocblas ] && [ ! -d %{buildroot}%{_libdir}/cmake/rocblas ]; then
	mkdir -p %{buildroot}%{_libdir}/cmake
	mv %{buildroot}/usr/lib/cmake/rocblas %{buildroot}%{_libdir}/cmake/
	rmdir %{buildroot}/usr/lib/cmake 2>/dev/null || true
	rmdir %{buildroot}/usr/lib 2>/dev/null || true
fi

%files
%license LICENSE.md
%doc README.md
%exclude %{_docdir}/rocblas/LICENSE.md
%{_libdir}/librocblas.so.*
# Tensile-generated library (code objects / msgpack library)
%{_libdir}/rocblas/

%files devel
%{_includedir}/rocblas/
%{_libdir}/librocblas.so
%{_libdir}/cmake/rocblas/
