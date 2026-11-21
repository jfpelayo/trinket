import { NativeTabs } from 'expo-router/native-tabs';

export default function TabLayout() {
    return (
        <NativeTabs>
            {/* <NativeTabs.Trigger name="index">
            <NativeTabs.Trigger.Label>Log In</NativeTabs.Trigger.Label>
            </NativeTabs.Trigger>
            <NativeTabs.Trigger name="createaccount">
                <NativeTabs.Trigger.Label>Create Account</NativeTabs.Trigger.Label>
            </NativeTabs.Trigger> */}
            <NativeTabs.Trigger name="testhomepage">
                <NativeTabs.Trigger.Label> Home </NativeTabs.Trigger.Label>
            </NativeTabs.Trigger>
            <NativeTabs.Trigger name="testshop">
                <NativeTabs.Trigger.Label> Shop </NativeTabs.Trigger.Label>
            </NativeTabs.Trigger>
            <NativeTabs.Trigger name="testchat">
                <NativeTabs.Trigger.Label> Chat </NativeTabs.Trigger.Label>
            </NativeTabs.Trigger>
        </NativeTabs>
    );
}