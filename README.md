syntaxnet
===

- description
  - test code for syntaxnet

- how to test
```
(after installing syntaxnet)
$ pwd
/root/syntaxnet/models/syntaxnet
$ git clone https://github.com/dsindex/syntaxnet.git work
$ cd work
$ echo "hello syntaxnet" | ./demo.sh
$ ./parser_trainer_test.sh 
```

- download univeral dependency treebank data 
  - http://universaldependencies.org/#en)
  ```
  mkdir corpus
  cd orpus
  (downloading ud-treebanks-v1.2.tgz)
  tar -zxvf ud-treebanks-v1.2.tgz  
  ls universal-dependencies-1.2 
  UD_Ancient_Greek  UD_Basque  UD_Czech ....
  ```

- training other corpus
```
(training UD_English)
$ ./train.sh
```
