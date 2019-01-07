package com.litianyi.single;

/**
 * @Auther: ICC18e697
 * @Date: 2018/11/22 08:35
 * @Description:
 */
public class MyPrototype {

    private MySingle mySingle;

    public MySingle getMySingle() {
        return mySingle;
    }

    public void setMySingle(MySingle mySingle) {
        this.mySingle = mySingle;
    }


    public  void add(String name) {
        mySingle.addSomeThings(name);
    }


    public static void main(String[] args) {
        MyPrototype prototype = new MyPrototype();
        MyPrototype prototype2 = new MyPrototype();
        MyPrototype prototype3 = new MyPrototype();
        prototype.setMySingle(MySingle.getMysingle());
        prototype2.setMySingle(MySingle.getMysingle());
        prototype3.setMySingle(MySingle.getMysingle());

        prototype.add("张三");
        prototype2.add("李四");
        prototype3.add("王五");




    }
}
