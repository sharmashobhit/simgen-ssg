# Installation

**simgen-ssg** supports Python >= 3.8.

## Docker installation (Recommended)

The image is available on Github Container Registry. You can pull the image using:

```bash
docker pull ghcr.io/sharmashobhit/simgen-ssg:latest
```

You can then run using the following command:

```bash
docker run -v .:/docs/ -p 8000:8000 ghcr.io/sharmashobhit/simgen-ssg:latest
```

## Installing the `simgen` binary

### Installing with `pip`

**simgen-ssg** is available [on PyPI](https://pypi.org/project/simgen-ssg/). Just run

```bash
pip install simgen-ssg
```

### Installing from source

To install **simgen-ssg** from source, first clone [the repository](https://github.com/sharmashobhit/simgen-ssg):

```bash
git clone https://github.com/sharmashobhit/simgen-ssg.git
cd simgen-ssg
```

Then run

```bash
pip install -e .
```

## Running the binary

Once you have installed the binary, you can run it using:

```bash
simgen serve  --dir /path/to/directory
```
