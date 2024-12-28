import React from "react";
import { useRouteError } from "react-router-dom";
import Logo from "@/components/Logo";

export default function ErrorPage() {
    const error: any = useRouteError();

    return (
        <div className="App">
            <div className="container mx-auto p-20">
                <div className="flex flex-col justify-center text-center items-center">
                    <h1 className="text-2xl font-bold mb-8">meow</h1>
                    <Logo />
                    <div className="w-full max-w-2xl mt-8">
                        <h2 className="text-xl font-semibold mb-4">Oops!</h2>
                        <p className="text-lg mb-4">
                            Sorry, an unexpected error has occurred.
                        </p>
                        <p className="text-gray-600 italic">
                            {error.statusText || error.message}
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}