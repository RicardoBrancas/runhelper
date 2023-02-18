# runhelper

`runhelper` is a small library that helps you logs metrics for your instances and stores them on a easy to parse CSV file.

## Tool-side Usage

Currently, there are three main types of metric supported.

#### Timer tags

Timer tags are used to time specific parts of your code.

```
runhelper.timer_start('my.tag')
time_sensit_code1()
time_sensit_code2()
runhelper.timer_stop('my.tag')
```

Times are accumulated during the execution of your tool.

#### Counter tags

Counter tags are used to count events

```
runhelper.tag_increment('my.tag')
```

You can optionally increment the tag by a value different than 1 (floats are also supported).

```
runhelper.tag_increment('my.tag', 3)
```

#### Custom tags

You can also log any custom values you want.

```
runhelper.log_any('my.tag', my_object)
```

#### Automatic logging at program termination

By default, `runhelper` logs all timer and counter tags on normal program termination. If you also want to log when the program is force terminated you need to register the SIGTERM handler:

```
runhelper.register_sigterm_handler()
```

If you wish to perform additional operations when a SIGTERM happens you can also pass a callback:

```
runhelper.register_sigterm_handler(callback_function)
```

## Evaluation-side Usage

The evaluation side of `runhelper` consists of a single class that encapsulates all functionality. The `Runner` class helps you run instances in parallel, supports timeouts and memouts (when used with `rulsolver`) and extracts all the tags logged from your tool into an easy to parse CSV file. The tool also allows you to transparently resume a previously running experiment, skipping all the instances that were executed already. The following snippet exemplifies its usage:

```
instances = [ INSTANCE_LIST ]

runner = Runner('path_to_runsolver', 'output_file.csv',
                 timeout=TIMELIMIT_IN_SECONDS,
                 memout=MEMLIMIT_IN_KBS,
                 pool_size=NUM_PROCESSES)
                 
for instance in instances:
    runner.schedule(instance, [TOOL_EXECUTABLE, ARG1, ARG2, ...], INSTANCE_OUTPUT_FILE)
    
runner.wait()
```

This code will, for each instance, call the command `TOOL_EXECUTABLE` with the arguments you specify and save its output to `INSTANCE_OUTPUT_FILE`. The result is a CSV file containing one line for each instance with some basic info, plus all the tags that you logged during the tool execution. Here is an example of an output file:

| instance | real | cpu | ram  | timeout | memout | my.tag.1 | my.tag.2 |
|----------|------|-----|------|---------|--------|----------|----------|
| i1       | 3.2  | 3.1 | 5600 | False   | False  | 0.34     | 6        |
| i2       | 10   | 9.8 | 6200 | True    | False  | 0.2      | 11       |
| i3       | 2.1  | 2   | 1200 | False   | False  | 0.01     | 3        |