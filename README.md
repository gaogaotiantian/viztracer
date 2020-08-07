# CodeSnap

[![build](https://github.com/gaogaotiantian/codesnap/workflows/build/badge.svg)](https://github.com/gaogaotiantian/codesnap/actions?query=workflow%3Abuild)  [![pypi](https://img.shields.io/pypi/v/codesnap.svg)](https://pypi.org/project/codesnap/)

CodeSnap is a light-weighted profiling tool that can visualize python code running result in flame graph. The major data CodeSnap displays is FEE(function entry/exit), or equivalently, the call stack. 

With CodeSnap, the programmer can intuitively understand what their code is doing and how long each function takes.  

## Requirements

CodeSnap requires python 3.5+. No other package is needed.

## Install

The prefered way to install CodeSnap is via pip

```
pip install codesnap
```

You can also download the source code and build it yourself.

## Usage

There are a couple ways to use CodeSnap

### Command Line

The easiest way to use CodeSnap it through command line. Assume you have a python script to profile and the normal way to run it is:

```
python3 my_script.py
```

You can simply use CodeSnap as 

```
python3 -m codesnap my_script.py
```

which will generate a ```result.html``` file in the directory you run this command. Open it in browser and there's your result.

If your script needs arguments like 

```
python3 my_script.py arg1 arg2
```

Just feed it as it is to CodeSnap

```
python3 -m codesnap my_script.py arg1 arg2
```

### Inline

Sometimes the command line may not work as you expected, or you do not want to profile the whole script. You can manually start/stop the profiling in your script as well.

First of all, you need to import ```CodeSnap``` class from the package, and make an object of it.

```python
from codesnap import CodeSnap

snap = CodeSnap()
```

If your code is executable by ```exec``` function, you can simply call ```snap.run()```

```python
snap.run("import random;random.randrange(10)")
```

This will as well generate a ```result.html``` file in your current directory. You can pass other file path to the function if you do not like the name ```result.html```

```python
snap.run("import random; random.randrange(10)", output_file = "better_name.html")
```

When you need a more delicate profiler, you can manually enable/disable the profile using ```start()``` and ```stop()``` function.

```python
snap.start()
# Something happens here
snap.stop()
snap.save() # also takes output_file as an optional argument
```

With this method, you can only record the part that you are interested in

```python
# Some code that I don't care
snap.start()
# Some code I do care
snap.stop()
# Some code that I want to skip
snap.start()
# Important code again
snap.stop()
snap.save()
```

**It is higly recommended that ```start()``` and ```stop()``` function should be in the same frame(same level on call stack). Problem might happen if the condition is not met**

## Limitations

CodeSnap uses ```sys.setprofile()``` for its profiler capabilities, so it will conflict with other profiling tools which also use this function. Be aware of it when using CodeSnap.

## Bugs/Requirements

Please send bug reports and feature requirements through [github issue tracker](https://github.com/gaogaotiantian/codesnap/issues). CodeSnap is currently under development now and it's open to any constructive suggestions.

## License

Copyright Tian Gao, 2020.

Distributed under the terms of the  [Apache 2.0 license](https://github.com/gaogaotiantian/codesnap/blob/master/LICENSE).