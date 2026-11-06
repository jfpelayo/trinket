import { f1 } from '@/constants/theme';
import { Image, ImageBackground } from 'expo-image';
import { useRef, useState } from 'react';
import { Pressable, ScrollView, Text, TextInput, View } from 'react-native';

// what the parrot always says for now (until the chatbot is connected)
const PARROT_REPLY = 'This is Placeholder Text.';

// one chat message: who sent it, and what it says
type Message = { from: 'parrot' | 'user'; text: string };

export default function ChatScreen() {
  // what's typed in the message box
  const [chatInput, setChatInput] = useState('');

  // every message the user has sent, in order
  const [UserChatRecord, setUserChatRecord] = useState<string[]>([]);

  // the whole conversation (both sides), used to draw the bubbles
  const [messages, setMessages] = useState<Message[]>([]);

  // lets us scroll the chat to the newest message
  const scrollRef = useRef<ScrollView>(null);

  // runs when Send is pressed (or Enter in the message box)
  function handleSend() {
    const text = chatInput.trim();
    if (!text) return; // ignore empty messages

    setUserChatRecord((prev) => [...prev, text]);
    setMessages((prev) => [
      ...prev,
      { from: 'user', text },
      { from: 'parrot', text: PARROT_REPLY },
    ]);
    setChatInput('');
  }

  return (
    <ImageBackground
      source={require('@/assets/images/ChatBG.png')}
        style={{ flex: 1 }}
    >

      {/* the conversation: only this area scrolls, the rest of the page stays still.
          top / bottom set where the scrolling area starts and stops */}
      <ScrollView
        ref={scrollRef}
        style={{ position: 'absolute', top: 180, height: 540, bottom: 100, left: 0, right: 0 }}
        contentContainerStyle={{ paddingHorizontal: 12, paddingVertical: 8, gap: 14 }}
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}>
        {messages.map((message, index) => (
          <ChatBubble key={index} message={message} />
        ))}
      </ScrollView>

      {/* the message box: positioned on its own */}
      <View style={{ position: 'absolute', top: 735, left: 50 }}>
        <ImageBackground
          source={require('@/assets/images/InputTextColor.png')}
          contentFit="fill"
          style={{ width: 330, height: 70, flexDirection: 'row', alignItems: 'center', borderRadius: 15, overflow: 'hidden', borderWidth: 2.5, borderColor: '#000' }}>
          <TextInput
            value={chatInput}
            onChangeText={setChatInput}
            onSubmitEditing={handleSend} // Enter key sends too
            placeholder="Type a message. Mate!"
            placeholderTextColor="#40300f"
            style={{ position: 'relative', flex: 1, minWidth: 0, padding: 15, fontSize: 22, color: '#040000', fontFamily: f1 }}
          />
        </ImageBackground>
      </View>

      {/* the Send button: positioned on its own */}
      <Pressable
          id="send"
          testID="send"
          accessibilityLabel="Send message"
          onPress={handleSend}
          // the icon is already a round button, so no box behind it; shrink a little when pressed
          style={({ pressed }) => ({
          position: 'absolute',
          top: 725,
          left: 370,
          transform: [{ scale: pressed ? 0.9 : 1 }],
        })}
      >
        <Image
          source={require('@/assets/images/Send.png')}
          contentFit="contain"
          style={{ width: 95, height: 95 }}
        />
      </Pressable>

      {/* custom icon: positioned on its own.
          swap the path for your image, then adjust top / left (position) and width / height (size) */}
      <Image
        source={require('@/assets/images/ChatBanner.png')} // placeholder: replace with your image
        contentFit="contain"
        style={{ position: 'absolute', top: 0, alignSelf: 'center', width: 250, height: 250 }}
      />

    </ImageBackground>
  );
}

// chat bubble look: change these to restyle every bubble
const AVATAR_SIZE = 42;
const BUBBLE_STYLE = {
  parrot: { background: '#FFF6E3', border: '#5a3410', text: '#3b2414' }, // cream parchment
  user: { background: '#D7392F', border: '#7a1d16', text: '#FFFFFF' }, // red, matches the Send button
};

// draws one message like a texting app:
// parrot on the left (icon, then bubble), user on the right (bubble, then icon)
function ChatBubble({ message }: { message: Message }) {
  const isParrot = message.from === 'parrot';
  const colors = isParrot ? BUBBLE_STYLE.parrot : BUBBLE_STYLE.user;

  return (
    <View
      style={{
        flexDirection: isParrot ? 'row' : 'row-reverse', // row-reverse puts the icon on the right
        alignItems: 'flex-end', // icon lines up with the bottom of the bubble
        alignSelf: isParrot ? 'flex-start' : 'flex-end', // left or right side of the screen
        gap: 8,
        maxWidth: '85%',
      }}>
      {/* round icon: overflow hidden + borderRadius crops the image to a circle */}
      <View style={{ width: AVATAR_SIZE, height: AVATAR_SIZE, borderRadius: AVATAR_SIZE / 2, overflow: 'hidden' }}>
        <Image
          source={isParrot ? require('@/assets/images/PaTalk.png') : require('@/assets/images/PiTalk.png')}
          contentFit="cover"
          style={{ width: '100%', height: '100%' }}
        />
      </View>

      {/* the speech bubble. the corner next to the icon is less rounded, like a little tail */}
      <View
        style={{
          flexShrink: 1, // lets long messages wrap instead of running off the screen
          paddingVertical: 10,
          paddingHorizontal: 14,
          borderRadius: 18,
          borderBottomLeftRadius: isParrot ? 4 : 18,
          borderBottomRightRadius: isParrot ? 18 : 4,
          borderWidth: 2,
          borderColor: colors.border,
          backgroundColor: colors.background,
        }}>
        <Text style={{ fontSize: 16, lineHeight: 21, color: colors.text }}>{message.text}</Text>
      </View>
    </View>
  );
}
