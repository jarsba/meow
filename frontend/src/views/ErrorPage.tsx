import { useRouteError } from "react-router-dom";
import { Container, Flex, Text, Card } from "@radix-ui/themes";
import Background from "@/components/Background";

export default function ErrorPage() {
  const error = useRouteError() as any;

  return (
    <Background>
      <Container size="3" className="py-8">
        <Flex direction="column" align="center" gap="6">
          <h1 className="text-2xl font-bold mb-8">meow</h1>
          
          <Card size="2" className="card-container w-full max-w-2xl p-6">
            <Flex direction="column" gap="4">
              <Text size="5" weight="bold">Oops!</Text>
              <Text size="3">Sorry, an unexpected error has occurred.</Text>
              <Text size="2" className="text-gray-500">
                {error.statusText || error.message}
              </Text>
            </Flex>
          </Card>
        </Flex>
      </Container>
    </Background>
  );
}